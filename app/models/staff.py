"""
Staff management models for the Bookora application.

This module contains models for managing business staff members,
their schedules, specialties, and availability.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum, Time, Date
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import time
import uuid

from app.models.base import BaseModel


class StaffRole(str, Enum):
    """Enumeration for staff roles."""
    OWNER = "owner"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    CONTRACTOR = "contractor"


class StaffMember(BaseModel):
    """
    Model representing a staff member at a business.
    
    Staff members can provide services, have their own schedules,
    and be assigned to specific appointments.
    """
    __tablename__ = "staff_members"
    
    # Business relationship
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, unique=True)
    phone_number = Column(String(20), nullable=True)
    
    # Profile
    profile_image_url = Column(String(500), nullable=True, comment="Staff member profile image URL")
    bio = Column(Text, nullable=True, comment="Staff bio and specialties description")
    
    # Role and Status
    role = Column(SQLEnum(StaffRole), default=StaffRole.EMPLOYEE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Professional Details
    job_title = Column(String(200), nullable=True, comment="Job title or position")
    specialties = Column(ARRAY(String), nullable=True, comment="Array of specialty areas")
    years_of_experience = Column(Integer, nullable=True, comment="Years of professional experience")
    
    # Service Associations (which services can this staff member provide)
    # Many-to-many relationship with services table
    
    # Commission and Payment
    commission_rate = Column(Integer, nullable=True, comment="Commission percentage (0-100)")
    hourly_rate = Column(Integer, nullable=True, comment="Hourly rate for the staff member")
    
    # Booking Settings
    accepts_bookings = Column(Boolean, default=True, nullable=False)
    max_appointments_per_day = Column(Integer, default=10, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="staff_members")
    working_hours = relationship("StaffWorkingHours", back_populates="staff_member", cascade="all, delete-orphan")
    # appointments = relationship("Appointment", back_populates="assigned_staff_member")
    
    @property
    def full_name(self) -> str:
        """Get staff member's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<StaffMember(name='{self.full_name}', business='{self.business.name if self.business else 'None'}')>"


class StaffWorkingHours(BaseModel):
    """
    Model for staff member working hours.
    
    Each staff member can have custom working hours that may differ
    from the business operating hours.
    """
    __tablename__ = "staff_working_hours"
    
    staff_member_id = Column(UUID(as_uuid=True), ForeignKey("staff_members.id"), nullable=False, index=True)
    
    # Day and time
    day_of_week = Column(Integer, nullable=False, comment="Day of week (0=Monday, 6=Sunday)")
    is_working = Column(Boolean, default=True, nullable=False)
    
    # Time slots
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Break times
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    
    # Relationships
    staff_member = relationship("StaffMember", back_populates="working_hours")
    
    def __repr__(self):
        if not self.is_working:
            return f"<StaffWorkingHours(day={self.day_of_week}: OFF)>"
        return f"<StaffWorkingHours(day={self.day_of_week}: {self.start_time}-{self.end_time})>"


class StaffTimeOff(BaseModel):
    """
    Model for tracking staff time-off requests and vacations.
    
    Allows staff members to block out dates when they are unavailable.
    """
    __tablename__ = "staff_time_off"
    
    staff_member_id = Column(UUID(as_uuid=True), ForeignKey("staff_members.id"), nullable=False, index=True)
    
    # Time off period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Reason and notes
    reason = Column(String(200), nullable=True, comment="Reason for time off (vacation, sick, etc.)")
    notes = Column(Text, nullable=True)
    
    # Approval status
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String(200), nullable=True, comment="Who approved the time off")
    
    # Relationships
    staff_member = relationship("StaffMember")
    
    def __repr__(self):
        return f"<StaffTimeOff(staff={self.staff_member.full_name if self.staff_member else 'None'}, {self.start_date} to {self.end_date})>"

