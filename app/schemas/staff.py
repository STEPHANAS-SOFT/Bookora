"""
Pydantic schemas for staff management API endpoints.

This module contains request and response schemas for managing business
staff members, their schedules, and time-off requests.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, time, date
import uuid

from app.models.staff import StaffRole


class StaffMemberCreate(BaseModel):
    """Schema for creating a new staff member."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    
    # Profile
    profile_image_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    
    # Role and professional details
    role: StaffRole = StaffRole.EMPLOYEE
    job_title: Optional[str] = Field(None, max_length=200)
    specialties: Optional[List[str]] = None
    years_of_experience: Optional[int] = Field(None, ge=0, le=100)
    
    # Commission and payment
    commission_rate: Optional[int] = Field(None, ge=0, le=100, description="Commission percentage")
    hourly_rate: Optional[int] = Field(None, ge=0, description="Hourly rate")
    
    # Booking settings
    accepts_bookings: bool = True
    max_appointments_per_day: Optional[int] = Field(None, ge=1, le=50)


class StaffMemberUpdate(BaseModel):
    """Schema for updating staff member information."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    
    # Profile
    profile_image_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    
    # Role and professional details
    role: Optional[StaffRole] = None
    job_title: Optional[str] = Field(None, max_length=200)
    specialties: Optional[List[str]] = None
    years_of_experience: Optional[int] = Field(None, ge=0, le=100)
    
    # Commission and payment
    commission_rate: Optional[int] = Field(None, ge=0, le=100)
    hourly_rate: Optional[int] = Field(None, ge=0)
    
    # Status
    is_active: Optional[bool] = None
    accepts_bookings: Optional[bool] = None
    max_appointments_per_day: Optional[int] = Field(None, ge=1, le=50)


class StaffMemberResponse(BaseModel):
    """Response schema for staff member data."""
    id: uuid.UUID
    business_id: uuid.UUID
    
    # Personal information
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str]
    phone_number: Optional[str]
    
    # Profile
    profile_image_url: Optional[str]
    bio: Optional[str]
    
    # Role and status
    role: StaffRole
    is_active: bool
    
    # Professional details
    job_title: Optional[str]
    specialties: Optional[List[str]]
    years_of_experience: Optional[int]
    
    # Commission and payment
    commission_rate: Optional[int]
    hourly_rate: Optional[int]
    
    # Booking settings
    accepts_bookings: bool
    max_appointments_per_day: Optional[int]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StaffWorkingHoursCreate(BaseModel):
    """Schema for creating staff working hours."""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    is_working: bool = True
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    
    @field_validator('end_time')
    @classmethod
    def validate_times(cls, v, info):
        """Ensure end time is after start time."""
        if v and info.data.get('start_time') and v <= info.data['start_time']:
            raise ValueError('End time must be after start time')
        return v


class StaffWorkingHoursResponse(BaseModel):
    """Response schema for staff working hours."""
    id: uuid.UUID
    staff_member_id: uuid.UUID
    day_of_week: int
    is_working: bool
    start_time: Optional[time]
    end_time: Optional[time]
    break_start: Optional[time]
    break_end: Optional[time]
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StaffTimeOffCreate(BaseModel):
    """Schema for creating staff time-off request."""
    start_date: date
    end_date: date
    reason: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        """Ensure end date is not before start date."""
        if v and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError('End date must be on or after start date')
        return v


class StaffTimeOffUpdate(BaseModel):
    """Schema for updating staff time-off request."""
    reason: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    is_approved: Optional[bool] = None
    approved_by: Optional[str] = Field(None, max_length=200)


class StaffTimeOffResponse(BaseModel):
    """Response schema for staff time-off."""
    id: uuid.UUID
    staff_member_id: uuid.UUID
    start_date: date
    end_date: date
    reason: Optional[str]
    notes: Optional[str]
    is_approved: bool
    approved_by: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StaffListResponse(BaseModel):
    """Response schema for paginated staff list."""
    staff_members: List[StaffMemberResponse]
    total: int
    skip: int
    limit: int

