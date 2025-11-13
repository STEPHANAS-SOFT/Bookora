"""
Business API endpoints for the Bookora application.

This module contains all API endpoints related to business management,
including registration, profile management, services, and business hours.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, time
import uuid

from app.core.database import get_db
from app.models.businesses import Business, BusinessCategory, Service, BusinessHours, BusinessStatus, WeekDay
from app.schemas.businesses import (
    BusinessCreate, BusinessUpdate, BusinessResponse, BusinessListResponse,
    ServiceCreate, ServiceUpdate, ServiceResponse,
    BusinessHoursCreate, BusinessHoursUpdate, BusinessHoursResponse,
    BusinessCategoryResponse
)
from app.core.auth import get_current_firebase_user

router = APIRouter()


# Business Categories
@router.get("/categories", response_model=List[BusinessCategoryResponse])
async def get_business_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)

):
    """
    Get all active business categories.
    
    Returns predefined categories like Hair Salon, Spa, Dentist, etc.
    Only administrators can manage categories.
    """
    categories = (
        db.query(BusinessCategory)
        .filter(BusinessCategory.is_active == True)
        .order_by(BusinessCategory.sort_order, BusinessCategory.name)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return categories


# Business Registration and Management
@router.post("/register", response_model=BusinessResponse)
async def register_business(
    business_data: BusinessCreate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """
    Register a new business.
    
    Creates a new business profile with the current Firebase user
    as the business owner. Business status is set to PENDING by default.
    """
    # Check if user already has a business
    existing_business = (
        db.query(Business)
        .filter(Business.firebase_uid == business_data.firebase_uid)
        .first()
    )
    
    if existing_business:
        raise HTTPException(
            status_code=400,
            detail="User already has a registered business"
        )
    
    # Verify category exists
    category = (
        db.query(BusinessCategory)
        .filter(BusinessCategory.id == business_data.category_id)
        .first()
    )
    
    if not category or not category.is_active:
        raise HTTPException(
            status_code=400,
            detail="Invalid business category"
        )
    
    # Create business
    business_dict = business_data.dict()
    firebase_uid = business_dict.pop('firebase_uid')
    owner_email = business_dict.pop('owner_email')
    
    business = Business(
        firebase_uid=firebase_uid,
        email=owner_email,
        email_verified=current_user.get("email_verified", False),
        **business_dict
    )
    
    # Set location if provided
    if business_data.latitude and business_data.longitude:
        business.set_location(business_data.latitude, business_data.longitude)
    
    # Generate unique booking slug
    if business_data.booking_slug:
        existing_slug = (
            db.query(Business)
            .filter(Business.booking_slug == business_data.booking_slug)
            .first()
        )
        if existing_slug:
            raise HTTPException(
                status_code=400,
                detail="Booking slug already exists"
            )
        business.booking_slug = business_data.booking_slug
    
    db.add(business)
    db.commit()
    db.refresh(business)
    
    return business


@router.get("/me", response_model=BusinessResponse)
async def get_my_business(
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Get current user's business profile."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    return business


@router.put("/me", response_model=BusinessResponse)
async def update_my_business(
    business_update: BusinessUpdate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Update current user's business profile."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    # Update fields
    update_data = business_update.dict(exclude_unset=True)
    
    # Handle location update
    if "latitude" in update_data and "longitude" in update_data:
        business.set_location(update_data.pop("latitude"), update_data.pop("longitude"))
    
    # Handle booking slug update
    if "booking_slug" in update_data and update_data["booking_slug"]:
        existing_slug = (
            db.query(Business)
            .filter(
                and_(
                    Business.booking_slug == update_data["booking_slug"],
                    Business.id != business.id
                )
            )
            .first()
        )
        if existing_slug:
            raise HTTPException(
                status_code=400,
                detail="Booking slug already exists"
            )
    
    for field, value in update_data.items():
        setattr(business, field, value)
    
    db.commit()
    db.refresh(business)
    
    return business


@router.get("/search", response_model=BusinessListResponse)
async def search_businesses(
    query: Optional[str] = Query(None, description="Search query for business name or description"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by business category"),
    latitude: Optional[float] = Query(None, description="Client latitude for proximity search"),
    longitude: Optional[float] = Query(None, description="Client longitude for proximity search"),
    radius_km: Optional[float] = Query(50.0, ge=1.0, le=100.0, description="Search radius in kilometers"),
    city: Optional[str] = Query(None, description="Filter by city"),
    status: Optional[BusinessStatus] = Query(BusinessStatus.ACTIVE, description="Filter by business status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)

):
    """
    Search businesses with various filters.
    
    Supports text search, category filtering, location-based proximity search,
    and city filtering. Results are ordered by relevance and distance.
    """
    query_filter = db.query(Business).filter(Business.status == status)
    
    # Text search
    if query:
        query_filter = query_filter.filter(
            or_(
                Business.name.ilike(f"%{query}%"),
                Business.description.ilike(f"%{query}%")
            )
        )
    
    # Category filter
    if category_id:
        query_filter = query_filter.filter(Business.category_id == category_id)
    
    # City filter
    if city:
        query_filter = query_filter.filter(Business.city.ilike(f"%{city}%"))
    
    # Location-based search
    if latitude and longitude:
        # Using PostGIS ST_DWithin for proximity search
        from geoalchemy2 import func as geo_func
        from geoalchemy2.elements import WKTElement
        
        point = WKTElement(f'POINT({longitude} {latitude})', srid=4826)
        
        query_filter = query_filter.filter(
            geo_func.ST_DWithin(
                Business.location,
                point,
                radius_km * 1000  # Convert km to meters
            )
        ).order_by(
            geo_func.ST_Distance(Business.location, point)
        )
    else:
        # Default ordering by name
        query_filter = query_filter.order_by(Business.name)
    
    # Get total count
    total = query_filter.count()
    
    # Apply pagination
    businesses = query_filter.offset(skip).limit(limit).all()
    
    return BusinessListResponse(
        businesses=businesses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/by-firebase-uid/{firebase_uid}", response_model=BusinessResponse)
async def get_business_by_firebase_uid(
    firebase_uid: str = Path(..., description="Firebase UID"),
    db: Session = Depends(get_db)

):
    """Get business by Firebase UID."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == firebase_uid)
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    return business

@router.put("/by-firebase-uid/{firebase_uid}", response_model=BusinessResponse)
async def update_business_by_firebase_uid(
    business_data: BusinessUpdate,
    firebase_uid: str = Path(..., description="Firebase UID"),
    db: Session = Depends(get_db)

):
    """Update business by Firebase UID."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == firebase_uid)
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    # Update business fields
    for field, value in business_data.dict(exclude_unset=True).items():
        if hasattr(business, field):
            setattr(business, field, value)
    
    business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(business)
    
    return business

@router.delete("/by-firebase-uid/{firebase_uid}")
async def delete_business_by_firebase_uid(
    firebase_uid: str = Path(..., description="Firebase UID"),
    db: Session = Depends(get_db)

):
    """Delete business by Firebase UID (soft delete)."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == firebase_uid)
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    # Soft delete - update status instead of actual deletion
    business.status = BusinessStatus.INACTIVE
    business.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Business successfully deactivated"}


@router.get("/slug/{booking_slug}", response_model=BusinessResponse)
async def get_business_by_slug(
    booking_slug: str = Path(..., description="Business booking slug"),
    db: Session = Depends(get_db)

):
    """Get business by booking slug for public booking page."""
    business = (
        db.query(Business)
        .filter(Business.booking_slug == booking_slug)
        .filter(Business.status == BusinessStatus.ACTIVE)
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    return business


# Business Services Management
@router.post("/me/services", response_model=ServiceResponse)
async def create_service(
    service_data: ServiceCreate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Create a new service for the current business."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    service = Service(
        business_id=business.id,
        **service_data.dict()
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service


@router.get("/me/services", response_model=List[ServiceResponse])
async def get_my_services(
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Get all services for the current business."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    services = (
        db.query(Service)
        .filter(Service.business_id == business.id)
        .order_by(Service.sort_order, Service.name)
        .all()
    )
    
    return services


@router.get("/{business_id}/services", response_model=List[ServiceResponse])
async def get_business_services(
    business_id: uuid.UUID = Path(..., description="Business ID"),
    active_only: bool = Query(True, description="Return only active services"),
    db: Session = Depends(get_db)

):
    """Get services for a specific business."""
    query_filter = db.query(Service).filter(Service.business_id == business_id)
    
    if active_only:
        query_filter = query_filter.filter(Service.is_active == True)
    
    services = (
        query_filter
        .order_by(Service.sort_order, Service.name)
        .all()
    )
    
    return services


@router.put("/me/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: uuid.UUID,
    service_update: ServiceUpdate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Update a service for the current business."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    service = (
        db.query(Service)
        .filter(
            and_(
                Service.id == service_id,
                Service.business_id == business.id
            )
        )
        .first()
    )
    
    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )
    
    # Update fields
    update_data = service_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    db.commit()
    db.refresh(service)
    
    return service


@router.delete("/me/services/{service_id}")
async def delete_service(
    service_id: uuid.UUID,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Delete a service for the current business."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    service = (
        db.query(Service)
        .filter(
            and_(
                Service.id == service_id,
                Service.business_id == business.id
            )
        )
        .first()
    )
    
    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )
    
    db.delete(service)
    db.commit()
    
    return {"message": "Service deleted successfully"}


# Business Hours Management
@router.post("/me/hours", response_model=List[BusinessHoursResponse])
async def set_business_hours(
    hours_data: List[BusinessHoursCreate],
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Set business hours for all days of the week."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    # Delete existing hours
    db.query(BusinessHours).filter(BusinessHours.business_id == business.id).delete()
    
    # Create new hours
    new_hours = []
    for hour_data in hours_data:
        business_hour = BusinessHours(
            business_id=business.id,
            **hour_data.dict()
        )
        db.add(business_hour)
        new_hours.append(business_hour)
    
    db.commit()
    
    # Refresh all objects
    for hour in new_hours:
        db.refresh(hour)
    
    return new_hours


@router.get("/me/hours", response_model=List[BusinessHoursResponse])
async def get_my_business_hours(
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Get business hours for the current business."""
    business = (
        db.query(Business)
        .filter(Business.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    
    hours = (
        db.query(BusinessHours)
        .filter(BusinessHours.business_id == business.id)
        .order_by(BusinessHours.day_of_week)
        .all()
    )
    
    return hours


@router.get("/{business_id}/hours", response_model=List[BusinessHoursResponse])
async def get_business_hours(
    business_id: uuid.UUID = Path(..., description="Business ID"),
    db: Session = Depends(get_db)

):
    """Get business hours for a specific business."""
    hours = (
        db.query(BusinessHours)
        .filter(BusinessHours.business_id == business_id)
        .order_by(BusinessHours.day_of_week)
        .all()
    )
    
    return hours