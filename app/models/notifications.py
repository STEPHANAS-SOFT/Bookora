"""
Notification domain models for the Bookora application.

This module contains models for managing email and push notifications,
including templates and notification logs.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from datetime import datetime
from typing import Dict, Any
import uuid

from app.models.base import BaseModel


class NotificationType(str, Enum):
    """Enumeration for notification types."""
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationEvent(str, Enum):
    """Enumeration for notification events."""
    APPOINTMENT_BOOKED = "appointment_booked"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_REMINDER_24H = "appointment_reminder_24h"
    APPOINTMENT_REMINDER_2H = "appointment_reminder_2h"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    APPOINTMENT_COMPLETED = "appointment_completed"
    NEW_MESSAGE = "new_message"
    BUSINESS_REVIEW_REQUEST = "business_review_request"
    CLIENT_REVIEW_REQUEST = "client_review_request"


class NotificationStatus(str, Enum):
    """Enumeration for notification status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationTemplate(BaseModel):
    """
    Model for notification templates.
    
    Stores reusable templates for different types of notifications
    with support for variable substitution.
    """
    __tablename__ = "notification_templates"
    
    # Template Identification
    name = Column(String(200), nullable=False, index=True)
    event = Column(SQLEnum(NotificationEvent), nullable=False, index=True)
    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    
    # Template Content
    subject = Column(String(500), nullable=True, comment="Email subject or push notification title")
    body = Column(Text, nullable=False, comment="Template body with variable placeholders")
    html_body = Column(Text, nullable=True, comment="HTML version for emails")
    
    # Template Settings
    is_active = Column(Boolean, default=True, nullable=False)
    language = Column(String(10), default="en", nullable=False)
    
    # Template Variables (JSON field with available variables)
    available_variables = Column(JSON, nullable=True, comment="List of available template variables")
    
    # Relationships
    notification_logs = relationship("NotificationLog", back_populates="template")
    
    def render(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Render template with provided variables.
        
        Args:
            variables: Dictionary of variables to substitute in template
            
        Returns:
            Dictionary with rendered subject and body
        """
        rendered_subject = self.subject
        rendered_body = self.body
        rendered_html_body = self.html_body
        
        # Replace variables in template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if rendered_subject:
                rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))
            if rendered_html_body:
                rendered_html_body = rendered_html_body.replace(placeholder, str(value))
        
        return {
            "subject": rendered_subject,
            "body": rendered_body,
            "html_body": rendered_html_body
        }
    
    def __repr__(self):
        return f"<NotificationTemplate(name='{self.name}', event={self.event}, type={self.notification_type})>"


class NotificationLog(BaseModel):
    """
    Model for logging sent notifications.
    
    Tracks all notifications sent through the system for
    audit purposes and delivery status monitoring.
    """
    __tablename__ = "notification_logs"
    
    # Template and Recipients
    template_id = Column(UUID(as_uuid=True), ForeignKey("notification_templates.id"), nullable=True)
    recipient_firebase_uid = Column(String(128), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    
    # Notification Details
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    event = Column(SQLEnum(NotificationEvent), nullable=False, index=True)
    
    # Content (rendered)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    html_body = Column(Text, nullable=True)
    
    # Delivery Status
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error Information
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # External Service Information
    external_id = Column(String(255), nullable=True, comment="ID from external service (SendGrid, FCM, etc.)")
    provider = Column(String(50), nullable=True, comment="Service provider used")
    
    # Related Entities
    related_appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    related_business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True)
    related_client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    
    # Additional Data (JSON field for flexibility)
    extra_data = Column(JSON, nullable=True, comment="Additional notification data")
    
    # Relationships
    template = relationship("NotificationTemplate", back_populates="notification_logs")
    related_appointment = relationship("Appointment")
    related_business = relationship("Business")
    related_client = relationship("Client")
    
    @property
    def is_delivered(self) -> bool:
        """Check if notification was successfully delivered."""
        return self.status == NotificationStatus.DELIVERED
    
    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return (self.status == NotificationStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def mark_sent(self):
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = func.now()
    
    def mark_delivered(self):
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = func.now()
    
    def mark_failed(self, error_message: str, error_code: str = None):
        """Mark notification as failed."""
        self.status = NotificationStatus.FAILED
        self.failed_at = func.now()
        self.error_message = error_message
        self.error_code = error_code
        self.retry_count += 1
    
    def __repr__(self):
        return f"<NotificationLog(type={self.notification_type}, event={self.event}, recipient={self.recipient_email or self.recipient_firebase_uid}, status={self.status})>"


class NotificationPreference(BaseModel):
    """
    Model representing user notification preferences.
    
    Controls which notifications users want to receive
    for different events and through different channels.
    """
    __tablename__ = "notification_preferences"
    
    # User associations (one of these will be set)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True, index=True)
    
    # Notification Configuration
    event = Column(SQLEnum(NotificationEvent), nullable=False)
    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timing Preferences
    send_at_hour = Column(Integer, nullable=True, comment="Preferred hour for notifications (0-23)")
    timezone = Column(String(50), nullable=True, comment="User's timezone for scheduling")
    
    # Frequency Control
    frequency_limit_per_day = Column(Integer, nullable=True, comment="Max notifications per day for this type")
    last_sent_date = Column(DateTime(timezone=True), nullable=True, comment="Last notification sent date")
    
    # Relationships
    client = relationship("Client", foreign_keys=[client_id])
    business = relationship("Business", foreign_keys=[business_id])
    
    def __repr__(self):
        user_type = "client" if self.client_id else "business"
        user_id = self.client_id or self.business_id
        return f"<NotificationPreference({user_type}={user_id}, event={self.event}, type={self.notification_type}, enabled={self.is_enabled})>"