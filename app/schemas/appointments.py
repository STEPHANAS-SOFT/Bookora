"""
Pydantic schemas for appointment-related API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.appointments import AppointmentStatus, CancellationReason


class AppointmentBase(BaseModel):
    """Base schema for appointment data."""
    appointment_date: datetime
    client_notes: Optional[str] = Field(None, max_length=1000)
    client_phone_override: Optional[str] = Field(None, max_length=20)


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment."""
    service_id: uuid.UUID


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""
    client_notes: Optional[str] = Field(None, max_length=1000)
    business_notes: Optional[str] = Field(None, max_length=1000)
    assigned_staff: Optional[str] = Field(None, max_length=200)


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling an appointment."""
    new_appointment_date: datetime


class AppointmentCancel(BaseModel):
    """Schema for cancelling an appointment."""
    reason: CancellationReason
    notes: Optional[str] = Field(None, max_length=1000)


class AppointmentResponse(BaseModel):
    """Response schema for appointment data."""
    id: uuid.UUID
    client_id: uuid.UUID
    business_id: uuid.UUID
    service_id: uuid.UUID
    
    # Appointment details
    appointment_date: datetime
    duration_minutes: int
    end_time: datetime
    status: AppointmentStatus
    confirmation_code: Optional[str]
    
    # Pricing
    service_price: Optional[Decimal]
    deposit_amount: Optional[Decimal]
    total_amount: Optional[Decimal]
    
    # Notes
    client_notes: Optional[str]
    business_notes: Optional[str]
    assigned_staff: Optional[str]
    
    # Status flags
    is_upcoming: bool
    is_today: bool
    can_be_cancelled: bool
    can_be_rescheduled: bool
    
    # Cancellation info
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[CancellationReason]
    cancellation_notes: Optional[str]
    cancelled_by_client: Optional[bool]
    
    # Completion info
    completed_at: Optional[datetime]
    actual_duration: Optional[int]
    
    # Ratings
    client_rating: Optional[int]
    client_review: Optional[str]
    business_rating: Optional[int]
    business_review: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    """Response schema for appointment list with pagination."""
    appointments: List[AppointmentResponse]
    total: int
    skip: int
    limit: int