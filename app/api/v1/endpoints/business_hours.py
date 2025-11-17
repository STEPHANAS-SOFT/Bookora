"""
Business Hours Management API endpoints for the Bookora application.

This module handles business operating hours configuration,
allowing businesses to set their weekly schedule.

Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, time
import uuid

from app.core.database import get_db
from app.models.businesses import Business, BusinessHours, WeekDay
from app.schemas.businesses import BusinessHoursCreate, BusinessHoursUpdate, BusinessHoursResponse

router = APIRouter()


@router.get("/", response_model=List[BusinessHoursResponse])
async def get_business_hours(
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get all operating hours for the business.
    Business owner only.
    Returns hours for all days of the week.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get all business hours ordered by day
    hours = (
        db.query(BusinessHours)
        .filter(BusinessHours.business_id == business.id)
        .order_by(BusinessHours.day_of_week)
        .all()
    )
    
    return hours


@router.get("/public/{business_id}", response_model=List[BusinessHoursResponse])
async def get_business_hours_public(
    business_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get business operating hours (public endpoint).
    Anyone can view business hours to know when they're open.
    """
    # Verify business exists
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.is_active == True
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get all business hours
    hours = (
        db.query(BusinessHours)
        .filter(BusinessHours.business_id == business_id)
        .order_by(BusinessHours.day_of_week)
        .all()
    )
    
    return hours


@router.post("/", response_model=BusinessHoursResponse)
async def create_business_hours(
    hours_data: BusinessHoursCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Set operating hours for a specific day.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if hours already exist for this day
    existing_hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business.id,
        BusinessHours.day_of_week == hours_data.day_of_week
    ).first()
    
    if existing_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Hours already exist for {hours_data.day_of_week}. Use PUT to update."
        )
    
    # Validate times if not closed
    if not hours_data.is_closed:
        if not hours_data.open_time or not hours_data.close_time:
            raise HTTPException(
                status_code=400,
                detail="Open and close times are required when business is not closed"
            )
        
        if hours_data.open_time >= hours_data.close_time:
            raise HTTPException(
                status_code=400,
                detail="Close time must be after open time"
            )
        
        # Validate break times if provided
        if hours_data.break_start and hours_data.break_end:
            if hours_data.break_start >= hours_data.break_end:
                raise HTTPException(
                    status_code=400,
                    detail="Break end time must be after break start time"
                )
            
            if hours_data.break_start < hours_data.open_time or hours_data.break_end > hours_data.close_time:
                raise HTTPException(
                    status_code=400,
                    detail="Break times must be within operating hours"
                )
    
    # Create business hours
    business_hours = BusinessHours(
        business_id=business.id,
        **hours_data.model_dump()
    )
    
    db.add(business_hours)
    db.commit()
    db.refresh(business_hours)
    
    return business_hours


@router.put("/{hours_id}", response_model=BusinessHoursResponse)
async def update_business_hours(
    hours_id: uuid.UUID,
    hours_update: BusinessHoursUpdate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update operating hours for a specific day.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get business hours
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.id == hours_id,
        BusinessHours.business_id == business.id
    ).first()
    
    if not business_hours:
        raise HTTPException(status_code=404, detail="Business hours not found")
    
    # Update fields
    update_data = hours_update.model_dump(exclude_unset=True)
    
    # Validate times if being updated
    if not update_data.get('is_closed', business_hours.is_closed):
        open_time = update_data.get('open_time', business_hours.open_time)
        close_time = update_data.get('close_time', business_hours.close_time)
        
        if open_time and close_time:
            if open_time >= close_time:
                raise HTTPException(
                    status_code=400,
                    detail="Close time must be after open time"
                )
        
        # Validate break times if provided
        break_start = update_data.get('break_start', business_hours.break_start)
        break_end = update_data.get('break_end', business_hours.break_end)
        
        if break_start and break_end:
            if break_start >= break_end:
                raise HTTPException(
                    status_code=400,
                    detail="Break end time must be after break start time"
                )
            
            if break_start < open_time or break_end > close_time:
                raise HTTPException(
                    status_code=400,
                    detail="Break times must be within operating hours"
                )
    
    # Apply updates
    for field, value in update_data.items():
        setattr(business_hours, field, value)
    
    business_hours.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(business_hours)
    
    return business_hours


@router.delete("/{hours_id}")
async def delete_business_hours(
    hours_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Delete operating hours for a specific day.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get and delete business hours
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.id == hours_id,
        BusinessHours.business_id == business.id
    ).first()
    
    if not business_hours:
        raise HTTPException(status_code=404, detail="Business hours not found")
    
    db.delete(business_hours)
    db.commit()
    
    return {"message": "Business hours deleted successfully"}


@router.post("/batch", response_model=List[BusinessHoursResponse])
async def set_batch_business_hours(
    hours_list: List[BusinessHoursCreate],
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Set operating hours for multiple days at once.
    Useful for setting up weekly schedule in one request.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    created_hours = []
    
    for hours_data in hours_list:
        # Check if hours already exist for this day
        existing_hours = db.query(BusinessHours).filter(
            BusinessHours.business_id == business.id,
            BusinessHours.day_of_week == hours_data.day_of_week
        ).first()
        
        if existing_hours:
            # Update existing hours
            update_data = hours_data.model_dump()
            for field, value in update_data.items():
                setattr(existing_hours, field, value)
            existing_hours.updated_at = datetime.utcnow()
            created_hours.append(existing_hours)
        else:
            # Create new hours
            business_hours = BusinessHours(
                business_id=business.id,
                **hours_data.model_dump()
            )
            db.add(business_hours)
            created_hours.append(business_hours)
    
    db.commit()
    
    # Refresh all objects
    for hours in created_hours:
        db.refresh(hours)
    
    return created_hours


@router.get("/check-availability", response_model=dict)
async def check_business_availability(
    business_id: uuid.UUID,
    check_date: str = Query(..., description="Date to check (YYYY-MM-DD format)"),
    db: Session = Depends(get_db)
):
    """
    Check if business is open on a specific date.
    Public endpoint - useful for clients to know if they can book.
    Returns opening hours and break times for the day.
    """
    from datetime import datetime
    
    # Parse date
    try:
        date_obj = datetime.strptime(check_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = date_obj.weekday()
    
    # Map to WeekDay enum
    weekday_map = {
        0: WeekDay.MONDAY,
        1: WeekDay.TUESDAY,
        2: WeekDay.WEDNESDAY,
        3: WeekDay.THURSDAY,
        4: WeekDay.FRIDAY,
        5: WeekDay.SATURDAY,
        6: WeekDay.SUNDAY
    }
    
    weekday = weekday_map[day_of_week]
    
    # Get business hours for this day
    hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business_id,
        BusinessHours.day_of_week == weekday
    ).first()
    
    if not hours:
        return {
            "is_open": False,
            "reason": "No hours configured for this day",
            "date": check_date,
            "day_of_week": weekday.value
        }
    
    if hours.is_closed:
        return {
            "is_open": False,
            "reason": "Business is closed on this day",
            "date": check_date,
            "day_of_week": weekday.value
        }
    
    return {
        "is_open": True,
        "date": check_date,
        "day_of_week": weekday.value,
        "open_time": hours.open_time.isoformat() if hours.open_time else None,
        "close_time": hours.close_time.isoformat() if hours.close_time else None,
        "break_start": hours.break_start.isoformat() if hours.break_start else None,
        "break_end": hours.break_end.isoformat() if hours.break_end else None
    }

