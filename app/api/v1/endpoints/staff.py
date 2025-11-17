"""
Staff Management API endpoints for the Bookora application.

This module handles business staff member management including
staff CRUD operations, working hours, and time-off requests.

Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime, date
import uuid

from app.core.database import get_db
from app.models.staff import StaffMember, StaffWorkingHours, StaffTimeOff
from app.models.businesses import Business
from app.schemas.staff import (
    StaffMemberCreate, StaffMemberUpdate, StaffMemberResponse, StaffListResponse,
    StaffWorkingHoursCreate, StaffWorkingHoursResponse,
    StaffTimeOffCreate, StaffTimeOffUpdate, StaffTimeOffResponse
)

router = APIRouter()


# Staff Member Management
@router.get("/", response_model=StaffListResponse)
async def get_business_staff(
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all staff members for a business.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Build query
    query = db.query(StaffMember).filter(StaffMember.business_id == business.id)
    
    # Apply filters
    if is_active is not None:
        query = query.filter(StaffMember.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    staff_members = (
        query.order_by(StaffMember.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return StaffListResponse(
        staff_members=staff_members,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{staff_id}", response_model=StaffMemberResponse)
async def get_staff_member(
    staff_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific staff member.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get staff member
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    return staff_member


@router.post("/", response_model=StaffMemberResponse)
async def create_staff_member(
    staff_data: StaffMemberCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Add a new staff member to the business.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if email already exists for this business (if provided)
    if staff_data.email:
        existing_staff = db.query(StaffMember).filter(
            StaffMember.business_id == business.id,
            StaffMember.email == staff_data.email
        ).first()
        if existing_staff:
            raise HTTPException(status_code=400, detail="Staff member with this email already exists")
    
    # Create staff member
    staff_member = StaffMember(
        business_id=business.id,
        **staff_data.model_dump()
    )
    
    db.add(staff_member)
    db.commit()
    db.refresh(staff_member)
    
    return staff_member


@router.put("/{staff_id}", response_model=StaffMemberResponse)
async def update_staff_member(
    staff_id: uuid.UUID,
    staff_update: StaffMemberUpdate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update a staff member's information.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get staff member
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Check email conflicts if email is being updated
    if staff_update.email and staff_update.email != staff_member.email:
        existing_staff = db.query(StaffMember).filter(
            StaffMember.business_id == business.id,
            StaffMember.email == staff_update.email,
            StaffMember.id != staff_id
        ).first()
        if existing_staff:
            raise HTTPException(status_code=400, detail="Staff member with this email already exists")
    
    # Update fields
    update_data = staff_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(staff_member, field, value)
    
    staff_member.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(staff_member)
    
    return staff_member


@router.delete("/{staff_id}")
async def delete_staff_member(
    staff_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) a staff member.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get staff member
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Soft delete (deactivate)
    staff_member.is_active = False
    staff_member.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Staff member deactivated successfully"}


# Working Hours Management
@router.get("/{staff_id}/working-hours", response_model=List[StaffWorkingHoursResponse])
async def get_staff_working_hours(
    staff_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get working hours for a staff member.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Get working hours
    working_hours = db.query(StaffWorkingHours).filter(
        StaffWorkingHours.staff_member_id == staff_id
    ).order_by(StaffWorkingHours.day_of_week).all()
    
    return working_hours


@router.post("/{staff_id}/working-hours", response_model=StaffWorkingHoursResponse)
async def create_staff_working_hours(
    staff_id: uuid.UUID,
    hours_data: StaffWorkingHoursCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Set working hours for a staff member for a specific day.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Check if hours already exist for this day
    existing_hours = db.query(StaffWorkingHours).filter(
        StaffWorkingHours.staff_member_id == staff_id,
        StaffWorkingHours.day_of_week == hours_data.day_of_week
    ).first()
    
    if existing_hours:
        raise HTTPException(
            status_code=400, 
            detail=f"Working hours already exist for this day. Use PUT to update."
        )
    
    # Create working hours
    working_hours = StaffWorkingHours(
        staff_member_id=staff_id,
        **hours_data.model_dump()
    )
    
    db.add(working_hours)
    db.commit()
    db.refresh(working_hours)
    
    return working_hours


@router.put("/{staff_id}/working-hours/{hours_id}", response_model=StaffWorkingHoursResponse)
async def update_staff_working_hours(
    staff_id: uuid.UUID,
    hours_id: uuid.UUID,
    hours_update: StaffWorkingHoursCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update working hours for a staff member.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Get working hours
    working_hours = db.query(StaffWorkingHours).filter(
        StaffWorkingHours.id == hours_id,
        StaffWorkingHours.staff_member_id == staff_id
    ).first()
    
    if not working_hours:
        raise HTTPException(status_code=404, detail="Working hours not found")
    
    # Update fields
    update_data = hours_update.model_dump()
    for field, value in update_data.items():
        setattr(working_hours, field, value)
    
    working_hours.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(working_hours)
    
    return working_hours


# Time Off Management
@router.get("/{staff_id}/time-off", response_model=List[StaffTimeOffResponse])
async def get_staff_time_off(
    staff_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    upcoming_only: bool = Query(False, description="Only show upcoming/future time-off"),
    db: Session = Depends(get_db)
):
    """
    Get time-off requests for a staff member.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Build query
    query = db.query(StaffTimeOff).filter(StaffTimeOff.staff_member_id == staff_id)
    
    if upcoming_only:
        query = query.filter(StaffTimeOff.end_date >= date.today())
    
    time_off = query.order_by(StaffTimeOff.start_date.desc()).all()
    
    return time_off


@router.post("/{staff_id}/time-off", response_model=StaffTimeOffResponse)
async def create_time_off_request(
    staff_id: uuid.UUID,
    time_off_data: StaffTimeOffCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Create a time-off request for a staff member.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Check for overlapping time-off
    overlapping = db.query(StaffTimeOff).filter(
        StaffTimeOff.staff_member_id == staff_id,
        StaffTimeOff.start_date <= time_off_data.end_date,
        StaffTimeOff.end_date >= time_off_data.start_date
    ).first()
    
    if overlapping:
        raise HTTPException(
            status_code=400,
            detail="Time-off request overlaps with existing time-off"
        )
    
    # Create time-off request
    time_off = StaffTimeOff(
        staff_member_id=staff_id,
        **time_off_data.model_dump()
    )
    
    db.add(time_off)
    db.commit()
    db.refresh(time_off)
    
    return time_off


@router.put("/{staff_id}/time-off/{time_off_id}", response_model=StaffTimeOffResponse)
async def update_time_off_request(
    staff_id: uuid.UUID,
    time_off_id: uuid.UUID,
    time_off_update: StaffTimeOffUpdate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update or approve a time-off request.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Get time-off request
    time_off = db.query(StaffTimeOff).filter(
        StaffTimeOff.id == time_off_id,
        StaffTimeOff.staff_member_id == staff_id
    ).first()
    
    if not time_off:
        raise HTTPException(status_code=404, detail="Time-off request not found")
    
    # Update fields
    update_data = time_off_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(time_off, field, value)
    
    time_off.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(time_off)
    
    return time_off


@router.delete("/{staff_id}/time-off/{time_off_id}")
async def delete_time_off_request(
    staff_id: uuid.UUID,
    time_off_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Delete a time-off request.
    Business owner only.
    """
    # Verify business ownership and staff member
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    staff_member = db.query(StaffMember).filter(
        StaffMember.id == staff_id,
        StaffMember.business_id == business.id
    ).first()
    
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Get and delete time-off request
    time_off = db.query(StaffTimeOff).filter(
        StaffTimeOff.id == time_off_id,
        StaffTimeOff.staff_member_id == staff_id
    ).first()
    
    if not time_off:
        raise HTTPException(status_code=404, detail="Time-off request not found")
    
    db.delete(time_off)
    db.commit()
    
    return {"message": "Time-off request deleted successfully"}

