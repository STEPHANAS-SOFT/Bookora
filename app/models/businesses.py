"""
Business domain models for the Bookora application.

This module contains all models related to businesses, including:
- Business entities (hair salons, spas, dentists, etc.)
- Business categories and services
- Business hours and availability
- Business settings and preferences
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, Time, ForeignKey, Enum as SQLEnum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from enum import Enum
from typing import List, Optional
from datetime import time
import uuid

from app.models.base import BaseModel, LocationMixin, FirebaseUserMixin


class BusinessStatus(str, Enum):
    """Enumeration for business status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class WeekDay(str, Enum):
    """Enumeration for days of the week."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class BusinessCategory(BaseModel):
    """
    Model for business categories (Hair Salon, Spa, Dentist, etc.).
    
    This model stores predefined business categories that can only be
    managed by administrators. Each business must belong to a category.
    """
    __tablename__ = "business_categories"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(500), nullable=True, comment="URL to category icon")
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, comment="Display order for categories")
    
    # Relationships
    businesses = relationship("Business", back_populates="category")
    
    def __repr__(self):
        return f"<BusinessCategory(name='{self.name}')>"


class Business(BaseModel, LocationMixin, FirebaseUserMixin):
    """
    Model representing a business (Hair Salon, Spa, Dentist, etc.).
    
    This is the core business entity that contains all information
    about a business including location, contact details, and settings.
    """
    __tablename__ = "businesses"
    
    # Basic Information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    
    # Category
    category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id"), nullable=False)
    
    # Contact Information  
    business_phone = Column(String(20), nullable=True)
    business_email = Column(String(255), nullable=True)
    
    # Business Settings
    status = Column(SQLEnum(BusinessStatus), default=BusinessStatus.PENDING, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether business is active")
    is_approved = Column(Boolean, default=False, nullable=False, comment="Whether business is approved by admin")
    timezone = Column(String(50), default="UTC", nullable=False, comment="Business timezone for appointments")
    
    # Booking Settings
    advance_booking_days = Column(Integer, default=30, comment="How many days in advance clients can book")
    min_advance_hours = Column(Integer, default=2, comment="Minimum hours in advance for booking")
    default_service_duration = Column(Integer, default=30, comment="Default service duration in minutes")
    
    # Business Metrics
    average_rating = Column(DECIMAL(3, 2), default=0.0, comment="Average rating from reviews")
    total_reviews = Column(Integer, default=0, comment="Total number of reviews")
    total_appointments = Column(Integer, default=0, comment="Total completed appointments")
    
    # Booking Link
    booking_slug = Column(String(100), unique=True, nullable=True, index=True, comment="Unique slug for booking link")
    
    # Profile Images
    logo_url = Column(String(500), nullable=True, comment="Business logo URL")
    cover_image_url = Column(String(500), nullable=True, comment="Business cover image URL")
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    
    # Relationships
    category = relationship("BusinessCategory", back_populates="businesses")
    services = relationship("Service", back_populates="business", cascade="all, delete-orphan")
    business_hours = relationship("BusinessHours", back_populates="business", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="business")
    staff_members = relationship("StaffMember", back_populates="business", cascade="all, delete-orphan")
    
    @hybrid_property
    def booking_url(self) -> str:
        """Generate booking URL for the business."""
        if self.booking_slug:
            return f"https://bookora.com/book/{self.booking_slug}"
        return f"https://bookora.com/book/{self.id}"
    
    def __repr__(self):
        return f"<Business(name='{self.name}', category='{self.category.name if self.category else 'None'}')>"


class Service(BaseModel):
    """
    Model for services offered by a business.
    
    Each business can offer multiple services with different
    durations, prices, and descriptions.
    """
    __tablename__ = "services"
    
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, comment="Service duration in minutes")
    price = Column(DECIMAL(10, 2), nullable=True, comment="Service price")
    
    # Service image
    service_image_url = Column(String(500), nullable=True, comment="Service image URL")
    
    # Service Settings
    is_active = Column(Boolean, default=True, nullable=False)
    requires_deposit = Column(Boolean, default=False)
    deposit_amount = Column(DECIMAL(10, 2), nullable=True)
    
    # Booking Rules
    max_advance_days = Column(Integer, nullable=True, comment="Override business advance booking days")
    min_advance_hours = Column(Integer, nullable=True, comment="Override business min advance hours")
    
    # Display Settings
    sort_order = Column(Integer, default=0, comment="Display order for services")
    color_code = Column(String(7), nullable=True, comment="Hex color code for calendar display")
    
    # Relationships
    business = relationship("Business", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")
    
    def __repr__(self):
        return f"<Service(name='{self.name}', business='{self.business.name if self.business else 'None'}')>"


class BusinessHours(BaseModel):
    """
    Model for business operating hours.
    
    Stores the operating hours for each day of the week.
    Supports multiple time slots per day and closed days.
    """
    __tablename__ = "business_hours"
    
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    day_of_week = Column(SQLEnum(WeekDay), nullable=False)
    is_closed = Column(Boolean, default=False, nullable=False)
    
    # Time slots (can have multiple per day)
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    
    # Break times (lunch break, etc.)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="business_hours")
    
    def __repr__(self):
        if self.is_closed:
            return f"<BusinessHours({self.day_of_week}: CLOSED)>"
        return f"<BusinessHours({self.day_of_week}: {self.open_time}-{self.close_time})>"


class BusinessGallery(BaseModel):
    """
    Model for business photo gallery.
    
    Stores multiple photos/images for a business to showcase
    their work, facilities, and services.
    """
    __tablename__ = "business_gallery"
    
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Image details
    image_url = Column(String(500), nullable=False, comment="Image URL")
    image_title = Column(String(200), nullable=True, comment="Image title or caption")
    image_description = Column(Text, nullable=True, comment="Image description")
    
    # Display settings
    sort_order = Column(Integer, default=0, comment="Display order in gallery")
    is_primary = Column(Boolean, default=False, comment="Primary/featured image")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Image metadata
    image_type = Column(String(50), nullable=True, comment="Type: exterior, interior, work_sample, team, etc.")
    
    # Relationships
    business = relationship("Business", backref="gallery_images")
    
    def __repr__(self):
        return f"<BusinessGallery(business={self.business.name if self.business else 'None'}, title='{self.image_title}')>"