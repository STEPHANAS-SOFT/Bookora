"""
Pydantic schemas for favorite business API endpoints.

This module contains request and response schemas for managing
client favorite businesses and business collections.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class FavoriteBusinessCreate(BaseModel):
    """Schema for adding a business to favorites."""
    business_id: uuid.UUID
    notes: Optional[str] = None
    notify_on_availability: bool = False
    notify_on_promotions: bool = True


class FavoriteBusinessUpdate(BaseModel):
    """Schema for updating favorite business settings."""
    notes: Optional[str] = None
    notify_on_availability: Optional[bool] = None
    notify_on_promotions: Optional[bool] = None


class FavoriteBusinessResponse(BaseModel):
    """Response schema for favorite business data."""
    id: uuid.UUID
    client_id: uuid.UUID
    business_id: uuid.UUID
    
    # Settings
    notes: Optional[str]
    notify_on_availability: bool
    notify_on_promotions: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Optional: Include business details in response
    # business: Optional[BusinessResponse] = None
    
    model_config = {"from_attributes": True}


class FavoriteBusinessListResponse(BaseModel):
    """Response schema for paginated favorite business list."""
    favorites: List[FavoriteBusinessResponse]
    total: int
    skip: int
    limit: int


class BusinessCollectionCreate(BaseModel):
    """Schema for creating a business collection."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7, pattern=r'^#[0-9A-Fa-f]{6}$')
    is_private: bool = True


class BusinessCollectionUpdate(BaseModel):
    """Schema for updating a business collection."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7, pattern=r'^#[0-9A-Fa-f]{6}$')
    is_private: Optional[bool] = None


class BusinessCollectionResponse(BaseModel):
    """Response schema for business collection data."""
    id: uuid.UUID
    client_id: uuid.UUID
    
    # Collection details
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_private: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Optional: Include count of businesses in collection
    business_count: Optional[int] = None
    
    model_config = {"from_attributes": True}


class BusinessCollectionItemCreate(BaseModel):
    """Schema for adding a business to a collection."""
    business_id: uuid.UUID
    notes: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)


class BusinessCollectionItemUpdate(BaseModel):
    """Schema for updating a business collection item."""
    notes: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)


class BusinessCollectionItemResponse(BaseModel):
    """Response schema for business collection item."""
    id: uuid.UUID
    collection_id: uuid.UUID
    business_id: uuid.UUID
    notes: Optional[str]
    sort_order: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Optional: Include business details
    # business: Optional[BusinessResponse] = None
    
    model_config = {"from_attributes": True}


class CollectionWithBusinessesResponse(BaseModel):
    """Response schema for collection with its businesses."""
    collection: BusinessCollectionResponse
    businesses: List[BusinessCollectionItemResponse]

