"""
Appointment API endpoints for the Bookora application.

This module handles appointment booking, management, and scheduling.
Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
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

router = APIRouter()

@router.post("/book", response_model=AppointmentResponse)
async def book_appointment(
    appointment_data: AppointmentCreate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Book a new appointment."""
    # Get client
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
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
                    Appointment.appointment_date + timedelta(minutes=Appointment.duration_minutes) > appointment_data.appointment_date
                ),
                and_(
                    Appointment.appointment_date < appointment_end,
                    Appointment.appointment_date >= appointment_data.appointment_date
                )
            )
        )
    ).first()
    
    if conflicts:
        raise HTTPException(status_code=409, detail="Time slot is already booked")
    
    # Create appointment
    appointment = Appointment(
        client_id=client.id,
        business_id=business.id,
        service_id=service.id,
        appointment_date=appointment_data.appointment_date,
        duration_minutes=service.duration_minutes,
        service_price=service.price,
        total_amount=service.price,
        client_notes=appointment_data.notes if hasattr(appointment_data, 'notes') else None,
        status=AppointmentStatus.PENDING
    )
    
    # Generate confirmation code
    appointment.generate_confirmation_code()
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.get("/my-appointments", response_model=AppointmentListResponse)
async def get_my_appointments(
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get appointments for the current user (client or business)."""
    
    # Check if user is a client
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    
    # Check if user is a business
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Build query
    query = db.query(Appointment)
    
    if client:
        query = query.filter(Appointment.client_id == client.id)
    else:
        query = query.filter(Appointment.business_id == business.id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    appointments = (
        query.order_by(Appointment.appointment_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return AppointmentListResponse(
        appointments=appointments,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: uuid.UUID = Path(..., description="Appointment ID"),
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Get a specific appointment by ID."""
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user has access to this appointment
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    has_access = False
    if client and appointment.client_id == client.id:
        has_access = True
    elif business and appointment.business_id == business.id:
        has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return appointment


@router.put("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: uuid.UUID,
    status: AppointmentStatus,
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Update appointment status (business owners and clients can modify)."""
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user has access to modify this appointment
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    has_access = False
    if client and appointment.client_id == client.id:
        # Clients can only cancel appointments
        if status not in [AppointmentStatus.CANCELLED]:
            raise HTTPException(status_code=403, detail="Clients can only cancel appointments")
        has_access = True
    elif business and appointment.business_id == business.id:
        # Businesses can modify any status
        has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    appointment.status = status
    appointment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.put("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    reschedule_data: AppointmentReschedule,
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Reschedule an appointment."""
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user has access
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    has_access = False
    if client and appointment.client_id == client.id:
        has_access = True
    elif business and appointment.business_id == business.id:
        has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check for conflicts with new time
    appointment_end = reschedule_data.new_date + timedelta(minutes=appointment.duration_minutes)
    
    conflicts = db.query(Appointment).filter(
        and_(
            Appointment.business_id == appointment.business_id,
            Appointment.id != appointment.id,
            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
            or_(
                and_(
                    Appointment.appointment_date <= reschedule_data.new_date,
                    Appointment.appointment_date + timedelta(minutes=Appointment.duration_minutes) > reschedule_data.new_date
                ),
                and_(
                    Appointment.appointment_date < appointment_end,
                    Appointment.appointment_date >= reschedule_data.new_date
                )
            )
        )
    ).first()
    
    if conflicts:
        raise HTTPException(status_code=409, detail="New time slot is already booked")
    
    # Update appointment
    appointment.appointment_date = reschedule_data.new_date
    appointment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


# Business-specific appointment endpoints
@router.get("/business/calendar", response_model=List[AppointmentResponse])
async def get_business_calendar(
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    start_date: datetime = Query(..., description="Start date for calendar"),
    end_date: datetime = Query(..., description="End date for calendar"),
    db: Session = Depends(get_db)
):
    """Get business calendar with all appointments in date range."""
    
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    appointments = db.query(Appointment).filter(
        and_(
            Appointment.business_id == business.id,
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date
        )
    ).order_by(Appointment.appointment_date).all()
    
    return appointments