"""
Pydantic schemas for notification-related API endpoints.

This module contains request and response schemas for managing notifications,
notification preferences, and notification logs.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.models.notifications import (
    NotificationType, 
    NotificationEvent, 
    NotificationStatus
)


class NotificationResponse(BaseModel):
    """Response schema for notification log data."""
    id: uuid.UUID
    
    # Recipient
    recipient_firebase_uid: str
    recipient_email: Optional[str]
    recipient_phone: Optional[str]
    
    # Notification details
    notification_type: NotificationType
    event: NotificationEvent
    
    # Content
    subject: Optional[str]
    body: str
    html_body: Optional[str]
    
    # Delivery status
    status: NotificationStatus
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    failed_at: Optional[datetime]
    
    # Error information
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    
    # Related entities
    related_appointment_id: Optional[uuid.UUID]
    related_business_id: Optional[uuid.UUID]
    related_client_id: Optional[uuid.UUID]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Response schema for paginated notification list."""
    notifications: List[NotificationResponse]
    total: int
    skip: int
    limit: int


class NotificationPreferenceResponse(BaseModel):
    """Response schema for notification preference."""
    id: uuid.UUID
    client_id: Optional[uuid.UUID]
    business_id: Optional[uuid.UUID]
    
    # Notification configuration
    event: NotificationEvent
    notification_type: NotificationType
    is_enabled: bool
    
    # Timing preferences
    send_at_hour: Optional[int]
    timezone: Optional[str]
    
    # Frequency control
    frequency_limit_per_day: Optional[int]
    last_sent_date: Optional[datetime]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences."""
    notification_type: NotificationType
    is_enabled: bool
    send_at_hour: Optional[int] = Field(None, ge=0, le=23, description="Preferred hour (0-23)")
    timezone: Optional[str] = Field(None, max_length=50)
    frequency_limit_per_day: Optional[int] = Field(None, ge=1, le=100)
    
    @field_validator('send_at_hour')
    @classmethod
    def validate_hour(cls, v):
        """Validate hour is within valid range."""
        if v is not None and (v < 0 or v > 23):
            raise ValueError('Hour must be between 0 and 23')
        return v


class FCMTokenUpdate(BaseModel):
    """Schema for updating FCM token."""
    fcm_token: str = Field(..., min_length=1, description="Firebase Cloud Messaging token")


class SendNotificationRequest(BaseModel):
    """Schema for manually sending a notification (admin use)."""
    recipient_firebase_uid: str
    notification_type: NotificationType
    event: NotificationEvent
    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None
    
    # Related entities
    related_appointment_id: Optional[uuid.UUID] = None
    related_business_id: Optional[uuid.UUID] = None
    related_client_id: Optional[uuid.UUID] = None
    
    # Additional data
    extra_data: Optional[Dict[str, Any]] = None

