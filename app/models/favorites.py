"""
Favorite business models for the Bookora application.

This module contains models for clients to save and manage their
favorite businesses for quick access and rebooking.
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel


class FavoriteBusiness(BaseModel):
    """
    Model representing a client's saved favorite business.
    
    Allows clients to bookmark businesses they like for easy access
    and quick rebooking of services.
    """
    __tablename__ = "favorite_businesses"
    
    # Relationships
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Metadata
    notes = Column(Text, nullable=True, comment="Personal notes about this business")
    
    # Notification preferences for this specific business
    notify_on_availability = Column(Boolean, default=False, comment="Notify when new slots available")
    notify_on_promotions = Column(Boolean, default=True, comment="Notify about promotions")
    
    # Add unique constraint to prevent duplicate favorites
    __table_args__ = (
        UniqueConstraint('client_id', 'business_id', name='unique_client_business_favorite'),
    )
    
    # Relationships
    client = relationship("Client", backref="favorite_businesses")
    business = relationship("Business", backref="favorited_by")
    
    def __repr__(self):
        client_name = self.client.full_name if self.client else "Unknown"
        business_name = self.business.name if self.business else "Unknown"
        return f"<FavoriteBusiness(client='{client_name}', business='{business_name}')>"


class BusinessCollection(BaseModel):
    """
    Model for organizing favorite businesses into collections/lists.
    
    Allows clients to create custom lists like "Hair Salons", "Spas", etc.
    """
    __tablename__ = "business_collections"
    
    # Owner
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    
    # Collection details
    name = Column(String(100), nullable=False, comment="Collection name")
    description = Column(Text, nullable=True, comment="Collection description")
    
    # Display settings
    icon = Column(String(50), nullable=True, comment="Icon identifier for UI")
    color = Column(String(7), nullable=True, comment="Hex color code")
    
    # Privacy
    is_private = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    client = relationship("Client", backref="business_collections")
    businesses = relationship("BusinessCollectionItem", back_populates="collection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BusinessCollection(name='{self.name}', client='{self.client.full_name if self.client else 'Unknown'}')>"


class BusinessCollectionItem(BaseModel):
    """
    Model for items within a business collection.
    
    Links businesses to collections with additional metadata.
    """
    __tablename__ = "business_collection_items"
    
    # Relationships
    collection_id = Column(UUID(as_uuid=True), ForeignKey("business_collections.id"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Item-specific data
    notes = Column(Text, nullable=True, comment="Notes about this business in this collection")
    sort_order = Column(String(50), default=0, comment="Display order within collection")
    
    # Add unique constraint
    __table_args__ = (
        UniqueConstraint('collection_id', 'business_id', name='unique_collection_business'),
    )
    
    # Relationships
    collection = relationship("BusinessCollection", back_populates="businesses")
    business = relationship("Business")
    
    def __repr__(self):
        return f"<BusinessCollectionItem(collection={self.collection_id}, business={self.business_id})>"

