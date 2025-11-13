"""
Appointment API endpoints for the Bookora application.

This module handles appointment booking, management, and scheduling.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.appointments import Appointment, AppointmentStatus
from app.models.businesses import Business, Service
from app.models.clients import Client
from app.schemas.appointments import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse,
    AppointmentListResponse, AppointmentReschedule
)
from app.core.auth import get_current_firebase_user

router = APIRouter()

@router.post("/book", response_model=AppointmentResponse)
async def book_appointment(
    appointment_data: AppointmentCreate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Book a new appointment."""
    # Get client
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Validate business and service
    service = db.query(Service).filter(Service.id == appointment_data.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    business = service.business
    if business.status != "active":
        raise HTTPException(status_code=400, detail="Business is not accepting appointments")
    
    # Check for scheduling conflicts
    appointment_end = appointment_data.appointment_date + timedelta(minutes=service.duration_minutes)
    
    conflicts = db.query(Appointment).filter(
        and_(
            Appointment.business_id == business.id,
            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
            or_(
                and_(
                    Appointment.appointment_date <= appointment_data.appointment_date,
                    func.datetime(Appointment.appointment_date, f"+{Appointment.duration_minutes} minutes") > appointment_data.appointment_date
                ),
                and_(
                    Appointment.appointment_date < appointment_end,
                    func.datetime(Appointment.appointment_date, f"+{Appointment.duration_minutes} minutes") >= appointment_end
                )
            )
        )
    ).first()
    
    if conflicts:
        raise HTTPException(status_code=400, detail="Time slot not available")
    
    # Create appointment
    appointment = Appointment(
        client_id=client.id,
        business_id=business.id,
        service_id=service.id,
        appointment_date=appointment_data.appointment_date,
        duration_minutes=service.duration_minutes,
        service_price=service.price,
        client_notes=appointment_data.client_notes,
        client_phone_override=appointment_data.client_phone_override
    )
    
    appointment.generate_confirmation_code()
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    return appointment

@router.get("/my-appointments", response_model=List[AppointmentResponse])
async def get_my_appointments(
    status: Optional[AppointmentStatus] = Query(None),
    upcoming_only: bool = Query(False),
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get appointments for current user (client or business)."""
    # Check if user is client or business
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client:
        query = db.query(Appointment).filter(Appointment.client_id == client.id)
    elif business:
        query = db.query(Appointment).filter(Appointment.business_id == business.id)
    else:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if upcoming_only:
        query = query.filter(Appointment.appointment_date > datetime.now())
    
    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get specific appointment details."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user has access to this appointment
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    has_access = False
    if client and appointment.client_id == client.id:
        has_access = True
    elif business and appointment.business_id == business.id:
        has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied to this appointment")
    
    return appointment


@router.put("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: uuid.UUID,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Confirm an appointment (business only)."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Only business can confirm appointments
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    if not business or appointment.business_id != business.id:
        raise HTTPException(status_code=403, detail="Only the business can confirm appointments")
    
    if appointment.status != AppointmentStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending appointments can be confirmed")
    
    appointment.status = AppointmentStatus.CONFIRMED
    appointment.confirmed_at = datetime.now()
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.put("/{appointment_id}/cancel", response_model=AppointmentResponse) 
async def cancel_appointment(
    appointment_id: uuid.UUID,
    cancellation_reason: Optional[str] = Query(None, max_length=500),
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Cancel an appointment."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user has access to this appointment
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    has_access = False
    if client and appointment.client_id == client.id:
        has_access = True
        appointment.cancelled_by_client = True
    elif business and appointment.business_id == business.id:
        has_access = True
        appointment.cancelled_by_business = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied to this appointment")
    
    if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed or already cancelled appointment")
    
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.now()
    if cancellation_reason:
        appointment.cancellation_reason = cancellation_reason
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.put("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: uuid.UUID,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Mark an appointment as completed (business only)."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Only business can complete appointments
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    if not business or appointment.business_id != business.id:
        raise HTTPException(status_code=403, detail="Only the business can complete appointments")
    
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Only confirmed appointments can be completed")
    
    appointment.status = AppointmentStatus.COMPLETED
    appointment.completed_at = datetime.now()
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.get("/business/{business_id}/available-slots")
async def get_available_slots(
    business_id: uuid.UUID,
    service_id: uuid.UUID,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get available time slots for a specific business service on a given date."""
    from datetime import datetime, timedelta
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Verify business and service exist
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    from app.models.businesses import Service
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.business_id == business_id)
        .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get business hours for the target date day
    from app.models.businesses import BusinessHours
    weekday = target_date.weekday()  # 0=Monday, 6=Sunday
    business_hours = (
        db.query(BusinessHours)
        .filter(
            BusinessHours.business_id == business_id,
            BusinessHours.day_of_week == weekday,
            BusinessHours.is_open == True
        )
        .first()
    )
    
    if not business_hours:
        return {"available_slots": [], "message": "Business is closed on this date"}
    
    # Get existing appointments for the date
    existing_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.business_id == business_id,
            Appointment.appointment_date.cast(db.query(func.date).subquery()) == target_date,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
        )
        .all()
    )
    
    # Generate available time slots
    available_slots = []
    current_time = datetime.combine(target_date, business_hours.open_time)
    end_time = datetime.combine(target_date, business_hours.close_time)
    
    while current_time + timedelta(minutes=service.duration_minutes) <= end_time:
        # Check if this slot conflicts with existing appointments
        slot_end = current_time + timedelta(minutes=service.duration_minutes)
        is_available = True
        
        for appointment in existing_appointments:
            appt_start = appointment.appointment_date
            appt_end = appt_start + timedelta(minutes=appointment.service_duration or service.duration_minutes)
            
            # Check for overlap
            if (current_time < appt_end and slot_end > appt_start):
                is_available = False
                break
        
        if is_available:
            available_slots.append({
                "start_time": current_time.strftime("%H:%M"),
                "end_time": slot_end.strftime("%H:%M"),
                "datetime": current_time.isoformat()
            })
        
        # Move to next slot (15-minute intervals)
        current_time += timedelta(minutes=15)
    
    return {
        "date": date,
        "business_name": business.name,
        "service_name": service.name,
        "service_duration": service.duration_minutes,
        "available_slots": available_slots
    }


@router.put("/{appointment_id}/review", response_model=AppointmentResponse)
async def add_review_rating(
    appointment_id: uuid.UUID,
    review_data: dict,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Add review and rating to completed appointment."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status != AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only review completed appointments")
    
    # Check if user has access to this appointment
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    rating = review_data.get("rating")
    review_text = review_data.get("review", "")
    
    # Validate rating
    if rating is not None and (rating < 1 or rating > 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    if client and appointment.client_id == client.id:
        # Client reviewing business
        if appointment.client_rating is not None:
            raise HTTPException(status_code=400, detail="You have already reviewed this appointment")
        appointment.client_rating = rating
        appointment.client_review = review_text
    elif business and appointment.business_id == business.id:
        # Business reviewing client
        if appointment.business_rating is not None:
            raise HTTPException(status_code=400, detail="You have already reviewed this appointment")
        appointment.business_rating = rating
        appointment.business_review = review_text
    else:
        raise HTTPException(status_code=403, detail="Access denied to this appointment")
    
    db.commit()
    db.refresh(appointment)
    
    return appointment