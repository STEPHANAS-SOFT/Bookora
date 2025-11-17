"""
Database models module for Bookora application.

This module imports all SQLAlchemy models to ensure they are registered
with the metadata for database table creation.
"""

from app.core.database import Base

# Import all models to register them with SQLAlchemy
from app.models.clients import Client
from app.models.businesses import Business, BusinessCategory, Service, BusinessHours, BusinessGallery
from app.models.appointments import Appointment
from app.models.communications import ChatRoom, ChatMessage
from app.models.notifications import NotificationTemplate, NotificationLog, NotificationPreference
from app.models.staff import StaffMember, StaffWorkingHours, StaffTimeOff
from app.models.reviews import Review, ReviewHelpfulness
from app.models.favorites import FavoriteBusiness, BusinessCollection, BusinessCollectionItem
from app.models.payments import PaymentMethod, PaymentTransaction

# Export Base for use in main.py
__all__ = ["Base"]
