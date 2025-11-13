"""
Base models for the Bookora application.

This module contains abstract base models and mixins that provide
common functionality across different domain models.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from datetime import datetime
import uuid

from app.core.database import Base


class BaseModel(Base):
    """
    Abstract base model that provides common fields for all entities.
    
    Includes:
    - UUID primary key for better security and distributed systems
    - Created and updated timestamps for audit trails
    - Soft delete functionality for data integrity
    """
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


class LocationMixin:
    """
    Mixin that provides location functionality using PostGIS.
    
    Contains:
    - Geography point field for exact coordinates
    - Address fields for human-readable location
    - Properties for easy coordinate access
    """
    
    # Geographic location using PostGIS Geography type
    location = Column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=True,
        comment="Geographic coordinates (longitude, latitude)"
    )
    
    # Human-readable address components
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    @property
    def latitude(self) -> float:
        """Get latitude from location point."""
        if self.location and hasattr(self.location, 'data'):
            # Extract latitude from PostGIS point
            return float(self.location.data.split(' ')[1].replace('(', ''))
        return None
    
    @property
    def longitude(self) -> float:
        """Get longitude from location point."""
        if self.location and hasattr(self.location, 'data'):
            # Extract longitude from PostGIS point
            return float(self.location.data.split(' ')[0].replace('POINT(', ''))
        return None
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.address, self.city, self.state, self.postal_code, self.country]
        return ', '.join(filter(None, parts))


class FirebaseUserMixin:
    """
    Mixin for Firebase authentication integration.
    
    Contains:
    - Firebase UID for user identification
    - FCM token for push notifications
    - Email and phone verification status
    """
    
    firebase_uid = Column(
        String(128), 
        unique=True, 
        nullable=False,
        index=True,
        comment="Firebase User ID for authentication"
    )
    
    fcm_token = Column(
        Text,
        nullable=True,
        comment="Firebase Cloud Messaging token for push notifications"
    )
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=True)
    
    # Verification status
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    
    def update_fcm_token(self, token: str):
        """Update FCM token for push notifications."""
        self.fcm_token = token


class TimestampedModel(Base):
    """
    Abstract model for entities that need timestamp tracking.
    Lighter version of BaseModel without UUID and soft delete.
    """
    __abstract__ = True
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)