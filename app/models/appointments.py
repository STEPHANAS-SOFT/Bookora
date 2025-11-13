"""
Appointment domain models for the Bookora application.

This module contains all models related to appointments, including
appointment status, scheduling, and appointment history.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Enum as SQLEnum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.models.base import BaseModel


class AppointmentStatus(str, Enum):
    """Enumeration for appointment status."""
    PENDING = "pending"          # Appointment requested but not confirmed
    CONFIRMED = "confirmed"      # Appointment confirmed by business
    IN_PROGRESS = "in_progress"  # Appointment currently happening
    COMPLETED = "completed"      # Appointment completed successfully
    CANCELLED = "cancelled"      # Cancelled by client or business
    NO_SHOW = "no_show"         # Client didn't show up
    RESCHEDULED = "rescheduled"  # Appointment was rescheduled


class CancellationReason(str, Enum):
    """Enumeration for cancellation reasons."""
    CLIENT_REQUEST = "client_request"
    BUSINESS_REQUEST = "business_request"
    EMERGENCY = "emergency"
    ILLNESS = "illness"
    WEATHER = "weather"
    NO_SHOW = "no_show"
    OTHER = "other"


class Appointment(BaseModel):
    """
    Model representing an appointment between a client and business.
    
    This is the core entity that manages the booking system,
    including scheduling, status tracking, and appointment details.
    """
    __tablename__ = "appointments"
    
    # Related Entities
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    
    # Appointment Details
    appointment_date = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False, comment="Appointment duration in minutes")
    
    # Status and Tracking
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.PENDING, nullable=False, index=True)
    confirmation_code = Column(String(20), unique=True, nullable=True, comment="Unique confirmation code")
    
    # Pricing
    service_price = Column(DECIMAL(10, 2), nullable=True, comment="Price at time of booking")
    deposit_amount = Column(DECIMAL(10, 2), nullable=True, comment="Deposit paid")
    total_amount = Column(DECIMAL(10, 2), nullable=True, comment="Total amount charged")
    
    # Client Information
    client_notes = Column(Text, nullable=True, comment="Special requests or notes from client")
    client_phone_override = Column(String(20), nullable=True, comment="Phone number for this appointment")
    
    # Business Information
    business_notes = Column(Text, nullable=True, comment="Internal notes from business")
    assigned_staff = Column(String(200), nullable=True, comment="Staff member assigned to appointment")
    
    # Cancellation Information
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(SQLEnum(CancellationReason), nullable=True)
    cancellation_notes = Column(Text, nullable=True)
    cancelled_by_client = Column(Boolean, nullable=True, comment="True if cancelled by client, False if by business")
    
    # Rescheduling Information
    original_appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    rescheduled_from = Column(DateTime(timezone=True), nullable=True, comment="Original appointment time")
    
    # Completion Information
    completed_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration = Column(Integer, nullable=True, comment="Actual duration in minutes")
    
    # Rating and Review
    client_rating = Column(Integer, nullable=True, comment="Client rating (1-5)")
    client_review = Column(Text, nullable=True, comment="Client review text")
    business_rating = Column(Integer, nullable=True, comment="Business rating of client (1-5)")
    business_review = Column(Text, nullable=True, comment="Business review of client")
    
    # Reminder Tracking
    reminder_24h_sent = Column(Boolean, default=False)
    reminder_2h_sent = Column(Boolean, default=False)
    confirmation_sent = Column(Boolean, default=False)
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    business = relationship("Business", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    original_appointment = relationship("Appointment", remote_side="Appointment.id")
    rescheduled_appointments = relationship("Appointment", back_populates="original_appointment")
    
    @property
    def end_time(self) -> datetime:
        """Calculate appointment end time."""
        return self.appointment_date + timedelta(minutes=self.duration_minutes)
    
    @property
    def is_upcoming(self) -> bool:
        """Check if appointment is in the future."""
        return self.appointment_date > datetime.now(self.appointment_date.tzinfo)
    
    @property
    def is_today(self) -> bool:
        """Check if appointment is today."""
        now = datetime.now(self.appointment_date.tzinfo)
        return self.appointment_date.date() == now.date()
    
    @property
    def can_be_cancelled(self) -> bool:
        """Check if appointment can still be cancelled."""
        if self.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            return False
        
        # Can't cancel if appointment is within 2 hours (configurable)
        now = datetime.now(self.appointment_date.tzinfo)
        time_until_appointment = self.appointment_date - now
        return time_until_appointment.total_seconds() > 2 * 3600  # 2 hours in seconds
    
    @property
    def can_be_rescheduled(self) -> bool:
        """Check if appointment can be rescheduled."""
        return self.can_be_cancelled and self.status not in [AppointmentStatus.IN_PROGRESS]
    
    @property
    def time_until_appointment(self) -> Optional[timedelta]:
        """Get time remaining until appointment."""
        if self.is_upcoming:
            now = datetime.now(self.appointment_date.tzinfo)
            return self.appointment_date - now
        return None
    
    def generate_confirmation_code(self) -> str:
        """Generate a unique confirmation code for the appointment."""
        import random
        import string
        
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.confirmation_code = code
        return code
    
    def mark_completed(self, actual_duration: Optional[int] = None):
        """Mark appointment as completed."""
        self.status = AppointmentStatus.COMPLETED
        self.completed_at = func.now()
        if actual_duration:
            self.actual_duration = actual_duration
    
    def cancel(self, reason: CancellationReason, notes: Optional[str] = None, cancelled_by_client: bool = True):
        """Cancel the appointment."""
        self.status = AppointmentStatus.CANCELLED
        self.cancelled_at = func.now()
        self.cancellation_reason = reason
        self.cancellation_notes = notes
        self.cancelled_by_client = cancelled_by_client
    
    def reschedule(self, new_datetime: datetime) -> 'Appointment':
        """
        Reschedule appointment to a new time.
        Creates a new appointment and marks this one as rescheduled.
        """
        # Mark current appointment as rescheduled
        self.status = AppointmentStatus.RESCHEDULED
        
        # Create new appointment with same details
        new_appointment = Appointment(
            client_id=self.client_id,
            business_id=self.business_id,
            service_id=self.service_id,
            appointment_date=new_datetime,
            duration_minutes=self.duration_minutes,
            service_price=self.service_price,
            deposit_amount=self.deposit_amount,
            client_notes=self.client_notes,
            client_phone_override=self.client_phone_override,
            original_appointment_id=self.id,
            rescheduled_from=self.appointment_date
        )
        
        return new_appointment
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, client={self.client.full_name if self.client else 'None'}, business={self.business.name if self.business else 'None'}, date={self.appointment_date}, status={self.status})>"