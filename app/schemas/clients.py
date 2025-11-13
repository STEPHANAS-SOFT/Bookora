"""
Pydantic schemas for client-related API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date
import uuid


class ClientBase(BaseModel):
    """Base schema for client data."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date]
    gender: Optional[str] = Field(None, max_length=20)
    
    # Location fields
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Preferences
    preferred_language: str = Field("en", max_length=10)
    timezone: str = Field("UTC", max_length=50)


class ClientCreate(ClientBase):
    """Schema for creating a new client."""
    firebase_uid: str = Field(..., description="Firebase UID from frontend authentication")
    email: str = Field(..., description="Client email address")


class ClientUpdate(ClientBase):
    """Schema for updating a client."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    
    # Notification preferences
    email_notifications: Optional[bool]
    push_notifications: Optional[bool]
    sms_notifications: Optional[bool]
    marketing_emails: Optional[bool]


class ClientResponse(BaseModel):
    """Response schema for client data."""
    id: uuid.UUID
    firebase_uid: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    age: Optional[int]
    gender: Optional[str]
    
    # Location
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    
    # Preferences
    preferred_language: str
    timezone: str
    
    # Profile
    profile_image_url: Optional[str]
    bio: Optional[str]
    
    # Verification status
    email_verified: bool
    phone_verified: bool
    
    # Account status
    is_active: bool
    is_blocked: bool
    
    # Statistics
    total_appointments: int
    completed_appointments: int
    completion_rate: float
    reliability_score: float
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}