"""
Client domain models for the Bookora application.

This module contains all models related to clients/customers who
book appointments with businesses.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, Date, DECIMAL
from sqlalchemy.orm import relationship
from datetime import date
from typing import Optional

from app.models.base import BaseModel, LocationMixin, FirebaseUserMixin


class Client(BaseModel, LocationMixin, FirebaseUserMixin):
    """
    Model representing a client/customer who books appointments.
    
    Clients can search for businesses, book appointments, chat with
    businesses, and manage their booking preferences.
    """
    __tablename__ = "clients"
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    
    # Profile Information
    profile_image_url = Column(String(500), nullable=True, comment="Client profile image URL")
    bio = Column(Text, nullable=True, comment="Client bio or notes")
    
    # Preferences
    preferred_language = Column(String(10), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False, comment="Client timezone for appointments")
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    
    # Marketing Preferences
    marketing_emails = Column(Boolean, default=False)
    promotional_notifications = Column(Boolean, default=False)
    
    # Client Metrics
    total_appointments = Column(Integer, default=0, comment="Total appointments booked")
    completed_appointments = Column(Integer, default=0, comment="Total completed appointments")
    cancelled_appointments = Column(Integer, default=0, comment="Total cancelled appointments")
    no_show_count = Column(Integer, default=0, comment="Number of no-shows")
    
    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False, comment="Blocked by admin or business")
    
    # Emergency Contact (Optional)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="client")
    
    @property
    def full_name(self) -> str:
        """Get client's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> Optional[int]:
        """Calculate client's age from date of birth."""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def completion_rate(self) -> float:
        """Calculate appointment completion rate."""
        if self.total_appointments == 0:
            return 0.0
        return (self.completed_appointments / self.total_appointments) * 100
    
    @property
    def reliability_score(self) -> float:
        """
        Calculate client reliability score based on completion rate and no-shows.
        Score ranges from 0.0 to 10.0.
        """
        if self.total_appointments == 0:
            return 10.0  # New clients start with perfect score
        
        completion_rate = self.completion_rate / 100  # Convert to decimal
        no_show_penalty = min(self.no_show_count * 0.5, 5.0)  # Max penalty of 5 points
        
        score = (completion_rate * 10) - no_show_penalty
        return max(0.0, min(10.0, score))  # Ensure score is between 0-10
    
    def __repr__(self):
        return f"<Client(name='{self.full_name}', email='{self.email}')>"