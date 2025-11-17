"""
Business API endpoints for the Bookora application.

This module handles business registration, profile management, and business-specific operations.
Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.businesses import (
    Business, BusinessCategory, Service, BusinessHours
)
from app.schemas.businesses import (
    BusinessCreate, BusinessUpdate, BusinessResponse, BusinessListResponse,
    BusinessCategoryResponse, ServiceCreate, ServiceUpdate, ServiceResponse
)

router = APIRouter()


# Business Categories (Public - No auth needed)
@router.get("/categories", response_model=List[BusinessCategoryResponse])
async def get_business_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all active business categories.
    Public endpoint - no authentication required.
    """
    categories = db.query(BusinessCategory).filter(
        BusinessCategory.is_active == True
    ).offset(skip).limit(limit).all()
    
    return categories


# Business Registration 
@router.post("/register", response_model=BusinessResponse)
async def register_business(
    business_data: BusinessCreate,
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Register a new business with Firebase UID."""
    
    # Check if business already exists for this Firebase UID
    existing_business = db.query(Business).filter(
        Business.firebase_uid == firebase_uid
    ).first()
    
    if existing_business:
        raise HTTPException(
            status_code=400,
            detail="Business already registered for this Firebase UID"
        )
    
    # Check if email already exists
    if business_data.email:
        existing_email = db.query(Business).filter(
            Business.email == business_data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    # Create business
    business_dict = business_data.model_dump(exclude={'firebase_uid'})
    
    business = Business(
        firebase_uid=firebase_uid,
        email_verified=False,  # Email verification handled by Firebase on frontend
        **business_dict
    )
    
    # Set location if provided
    if business_data.latitude and business_data.longitude:
        business.set_location(business_data.latitude, business_data.longitude)
    
    db.add(business)
    db.commit()
    db.refresh(business)
    
    return business


# Business Profile Management
@router.get("/me", response_model=BusinessResponse)
async def get_my_business(
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Get current user's business profile."""
    business = db.query(Business).filter(
        Business.firebase_uid == firebase_uid
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return business


@router.put("/me", response_model=BusinessResponse)
async def update_my_business(
    business_update: BusinessUpdate,
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """Update current user's business profile."""
    business = db.query(Business).filter(
        Business.firebase_uid == firebase_uid
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields
    update_data = business_update.model_dump(exclude_unset=True)
    
    # Check email conflicts if email is being updated
    if "email" in update_data and update_data["email"] != business.email:
        existing_email = db.query(Business).filter(
            Business.email == update_data["email"],
            Business.id != business.id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Apply updates
    for field, value in update_data.items():
        setattr(business, field, value)
    
    # Update location if provided
    if hasattr(business_update, 'latitude') and hasattr(business_update, 'longitude'):
        if business_update.latitude and business_update.longitude:
            business.set_location(business_update.latitude, business_update.longitude)
    
    business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(business)
    
    return business


# Public Business Search (No auth needed)
@router.get("/search", response_model=BusinessListResponse)
async def search_businesses(
    query: Optional[str] = Query(None, description="Search query"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category"),
    latitude: Optional[float] = Query(None, description="User latitude for proximity"),
    longitude: Optional[float] = Query(None, description="User longitude for proximity"), 
    radius_km: Optional[float] = Query(50.0, ge=1, le=100, description="Search radius in km"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search businesses with various filters.
    Public endpoint - no authentication required.
    """
    
    query_builder = db.query(Business).filter(
        Business.is_active == True,
        Business.is_approved == True
    )
    
    # Text search
    if query:
        search_filter = func.lower(func.concat(
            Business.name, " ", Business.description
        )).contains(query.lower())
        query_builder = query_builder.filter(search_filter)
    
    # Category filter
    if category_id:
        query_builder = query_builder.filter(Business.category_id == category_id)
    
    # Location proximity filter
    if latitude and longitude:
        # Use PostGIS distance calculation
        distance_filter = func.ST_DWithin(
            Business.location,
            func.ST_Point(longitude, latitude),
            radius_km * 1000  # Convert km to meters
        )
        query_builder = query_builder.filter(distance_filter)
        
        # Order by distance
        query_builder = query_builder.order_by(
            func.ST_Distance(Business.location, func.ST_Point(longitude, latitude))
        )
    
    # Rating filter
    if min_rating:
        query_builder = query_builder.filter(Business.average_rating >= min_rating)
    
    # Get total count
    total = query_builder.count()
    
    # Apply pagination
    businesses = query_builder.offset(skip).limit(limit).all()
    
    return BusinessListResponse(
        businesses=businesses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business_by_id(
    business_id: uuid.UUID = Path(..., description="Business ID"),
    db: Session = Depends(get_db)
):
    """
    Get business details by ID.
    Public endpoint - no authentication required.
    """
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.is_active == True
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return business


# Service Management Endpoints
@router.get("/{business_id}/services", response_model=List[ServiceResponse])
async def get_business_services(
    business_id: uuid.UUID = Path(..., description="Business ID"),
    include_inactive: bool = Query(False, description="Include inactive services"),
    db: Session = Depends(get_db)
):
    """
    Get all services for a business.
    Public endpoint - returns active services by default.
    """
    query = db.query(Service).filter(Service.business_id == business_id)
    
    if not include_inactive:
        query = query.filter(Service.is_active == True)
    
    services = query.order_by(Service.sort_order, Service.name).all()
    
    return services


@router.post("/me/services", response_model=ServiceResponse)
async def create_service(
    service_data: ServiceCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Create a new service for the business.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Create service
    service = Service(
        business_id=business.id,
        **service_data.model_dump()
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service


@router.put("/me/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: uuid.UUID,
    service_update: ServiceUpdate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update a service.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get service
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.business_id == business.id
    ).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Update service
    update_data = service_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    service.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(service)
    
    return service


@router.delete("/me/services/{service_id}")
async def delete_service(
    service_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Delete (soft delete) a service.
    Business owner only.
    """
    # Verify business ownership
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get service
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.business_id == business.id
    ).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Soft delete (mark as inactive)
    service.is_active = False
    service.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Service deleted successfully"}