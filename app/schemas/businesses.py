"""
Pydantic schemas for business-related API endpoints.

These schemas define the request/response models for business operations
including validation rules and serialization.
"""

from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime, time
from decimal import Decimal
import uuid

from app.models.businesses import BusinessStatus, WeekDay


class BusinessCategoryResponse(BaseModel):
    """Response schema for business categories."""
    id: uuid.UUID
    name: str
    description: Optional[str]
    icon_url: Optional[str]
    is_active: bool
    sort_order: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class BusinessBase(BaseModel):
    """Base schema for business data."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    website: Optional[str] = Field(None, max_length=500)
    business_phone: Optional[str] = Field(None, max_length=20)
    business_email: Optional[str] = Field(None, max_length=255)
    timezone: str = Field("UTC", max_length=50)
    
    # Location fields
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class BusinessCreate(BusinessBase):
    """Schema for creating a new business."""
    firebase_uid: str = Field(..., description="Firebase UID from frontend authentication")
    owner_email: str = Field(..., description="Business owner email address")
    category_id: uuid.UUID
    booking_slug: Optional[str] = Field(None, min_length=3, max_length=100)
    
    # Booking settings
    advance_booking_days: Optional[int] = Field(30, ge=1, le=365)
    min_advance_hours: Optional[int] = Field(2, ge=0, le=168)
    default_service_duration: Optional[int] = Field(30, ge=15, le=480)


class BusinessUpdate(BusinessBase):
    """Schema for updating a business."""
    category_id: Optional[uuid.UUID]
    booking_slug: Optional[str] = Field(None, min_length=3, max_length=100)
    status: Optional[BusinessStatus]
    
    # Booking settings
    advance_booking_days: Optional[int] = Field(None, ge=1, le=365)
    min_advance_hours: Optional[int] = Field(None, ge=0, le=168)
    default_service_duration: Optional[int] = Field(None, ge=15, le=480)
    
    # Notification preferences
    email_notifications: Optional[bool]
    push_notifications: Optional[bool]
    sms_notifications: Optional[bool]


class BusinessResponse(BaseModel):
    """Response schema for business data."""
    id: uuid.UUID
    firebase_uid: str
    name: str
    description: Optional[str]
    website: Optional[str]
    email: str
    business_phone: Optional[str]
    business_email: Optional[str]
    
    # Category information
    category_id: uuid.UUID
    category: Optional[BusinessCategoryResponse]
    
    # Location
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    
    # Status and settings
    status: BusinessStatus
    timezone: str
    
    # Booking settings
    advance_booking_days: int
    min_advance_hours: int
    default_service_duration: int
    
    # Metrics
    average_rating: Decimal
    total_reviews: int
    total_appointments: int
    
    # URLs
    booking_slug: Optional[str]
    booking_url: str
    logo_url: Optional[str]
    cover_image_url: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BusinessListResponse(BaseModel):
    """Response schema for business list with pagination."""
    businesses: List[BusinessResponse]
    total: int
    skip: int
    limit: int


# Service Schemas
class ServiceBase(BaseModel):
    """Base schema for service data."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    duration_minutes: int = Field(..., ge=15, le=480)
    price: Optional[Decimal] = Field(None, ge=0)
    
    # Service image (primary image)
    service_image_url: Optional[str] = Field(None, max_length=500)
    
    # Service settings
    requires_deposit: bool = False
    deposit_amount: Optional[Decimal] = Field(None, ge=0)
    
    # Display settings
    sort_order: int = Field(0, ge=0)
    color_code: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')


class ServiceCreate(ServiceBase):
    """Schema for creating a new service."""
    pass


class ServiceUpdate(ServiceBase):
    """Schema for updating a service."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    is_active: Optional[bool]
    
    # Booking rules
    max_advance_days: Optional[int] = Field(None, ge=1, le=365)
    min_advance_hours: Optional[int] = Field(None, ge=0, le=168)


class ServiceResponse(BaseModel):
    """Response schema for service data."""
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: Optional[str]
    duration_minutes: int
    price: Optional[Decimal]
    
    # Service image (primary image)
    service_image_url: Optional[str]
    
    # Service settings
    is_active: bool
    requires_deposit: bool
    deposit_amount: Optional[Decimal]
    
    # Booking rules
    max_advance_days: Optional[int]
    min_advance_hours: Optional[int]
    
    # Display settings
    sort_order: int
    color_code: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Business Hours Schemas
class BusinessHoursBase(BaseModel):
    """Base schema for business hours."""
    day_of_week: WeekDay
    is_closed: bool = False
    open_time: Optional[time]
    close_time: Optional[time]
    break_start: Optional[time]
    break_end: Optional[time]


class BusinessHoursCreate(BusinessHoursBase):
    """Schema for creating business hours."""
    pass


class BusinessHoursUpdate(BusinessHoursBase):
    """Schema for updating business hours."""
    pass


class BusinessHoursResponse(BaseModel):
    """Response schema for business hours."""
    id: uuid.UUID
    business_id: uuid.UUID
    day_of_week: WeekDay
    is_closed: bool
    open_time: Optional[time]
    close_time: Optional[time]
    break_start: Optional[time]
    break_end: Optional[time]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Business Gallery Schemas
class BusinessGalleryBase(BaseModel):
    """Base schema for business gallery images."""
    image_url: str = Field(..., max_length=500)
    image_title: Optional[str] = Field(None, max_length=200)
    image_description: Optional[str] = Field(None, max_length=1000)
    sort_order: int = Field(0, ge=0)
    is_primary: bool = False
    image_type: Optional[str] = Field(None, max_length=50)


class BusinessGalleryCreate(BusinessGalleryBase):
    """Schema for creating a business gallery image."""
    pass


class BusinessGalleryUpdate(BaseModel):
    """Schema for updating a business gallery image."""
    image_title: Optional[str] = Field(None, max_length=200)
    image_description: Optional[str] = Field(None, max_length=1000)
    sort_order: Optional[int] = Field(None, ge=0)
    is_primary: Optional[bool]
    is_active: Optional[bool]
    image_type: Optional[str] = Field(None, max_length=50)


class BusinessGalleryResponse(BaseModel):
    """Response schema for business gallery image."""
    id: uuid.UUID
    business_id: uuid.UUID
    image_url: str
    image_title: Optional[str]
    image_description: Optional[str]
    sort_order: int
    is_primary: bool
    is_active: bool
    image_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Service Gallery Schemas
class ServiceGalleryBase(BaseModel):
    """Base schema for service gallery images."""
    image_url: str = Field(..., max_length=500)
    image_title: Optional[str] = Field(None, max_length=200)
    image_description: Optional[str] = Field(None, max_length=1000)
    sort_order: int = Field(0, ge=0)
    is_primary: bool = False
    image_type: Optional[str] = Field(None, max_length=50)


class ServiceGalleryCreate(ServiceGalleryBase):
    """Schema for creating a service gallery image."""
    pass


class ServiceGalleryUpdate(BaseModel):
    """Schema for updating a service gallery image."""
    image_title: Optional[str] = Field(None, max_length=200)
    image_description: Optional[str] = Field(None, max_length=1000)
    sort_order: Optional[int] = Field(None, ge=0)
    is_primary: Optional[bool]
    is_active: Optional[bool]
    image_type: Optional[str] = Field(None, max_length=50)


class ServiceGalleryResponse(BaseModel):
    """Response schema for service gallery image."""
    id: uuid.UUID
    service_id: uuid.UUID
    image_url: str
    image_title: Optional[str]
    image_description: Optional[str]
    sort_order: int
    is_primary: bool
    is_active: bool
    image_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}