"""
Global Service Search API endpoints for the Bookora application.

This module provides comprehensive service search functionality
across all businesses with advanced filters.

Authentication is handled by API key middleware.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.businesses import Service, Business, BusinessCategory
from app.schemas.businesses import ServiceResponse

router = APIRouter()


@router.get("/search", response_model=List[dict])
async def search_services(
    query: Optional[str] = Query(None, description="Search query for service name or description"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by business category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    max_duration: Optional[int] = Query(None, ge=0, description="Maximum duration in minutes"),
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="User latitude for proximity"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="User longitude for proximity"),
    radius_km: Optional[float] = Query(50.0, ge=1, le=100, description="Search radius in kilometers"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    requires_deposit: Optional[bool] = Query(None, description="Filter by deposit requirement"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Global service search across all businesses.
    
    Searches for services with comprehensive filtering options:
    - Text search on service name and description
    - Price range filtering
    - Duration filtering
    - Location-based proximity search
    - Business category filtering
    - City/state filtering
    
    Returns services with their business information.
    Public endpoint.
    """
    # Build base query - join service with business
    query_builder = (
        db.query(Service, Business)
        .join(Business, Service.business_id == Business.id)
        .filter(
            Service.is_active == True,
            Business.is_active == True,
            Business.is_approved == True
        )
    )
    
    # Text search on service name and description
    if query:
        search_filter = or_(
            func.lower(Service.name).contains(query.lower()),
            func.lower(Service.description).contains(query.lower())
        )
        query_builder = query_builder.filter(search_filter)
    
    # Business category filter
    if category_id:
        query_builder = query_builder.filter(Business.category_id == category_id)
    
    # Price range filters
    if min_price is not None:
        query_builder = query_builder.filter(Service.price >= min_price)
    
    if max_price is not None:
        query_builder = query_builder.filter(Service.price <= max_price)
    
    # Duration filter
    if max_duration is not None:
        query_builder = query_builder.filter(Service.duration_minutes <= max_duration)
    
    # Deposit requirement filter
    if requires_deposit is not None:
        query_builder = query_builder.filter(Service.requires_deposit == requires_deposit)
    
    # Location filters
    if city:
        query_builder = query_builder.filter(
            func.lower(Business.city).contains(city.lower())
        )
    
    if state:
        query_builder = query_builder.filter(
            func.lower(Business.state).contains(state.lower())
        )
    
    # Geographic proximity search
    if latitude and longitude:
        from geoalchemy2 import func as geo_func
        from geoalchemy2.elements import WKTElement
        
        user_point = WKTElement(f'POINT({longitude} {latitude})', srid=4326)
        
        query_builder = (
            query_builder
            .filter(Business.location.isnot(None))
            .filter(
                geo_func.ST_DWithin(
                    Business.location,
                    user_point,
                    radius_km * 1000  # Convert km to meters
                )
            )
        )
    
    # Order by service name
    query_builder = query_builder.order_by(Service.name)
    
    # Apply pagination
    results = query_builder.offset(skip).limit(limit).all()
    
    # Format response with service and business details
    services_with_business = []
    for service, business in results:
        service_dict = {
            # Service information
            "service_id": str(service.id),
            "service_name": service.name,
            "service_description": service.description,
            "duration_minutes": service.duration_minutes,
            "price": float(service.price) if service.price else None,
            "service_image_url": service.service_image_url,
            "requires_deposit": service.requires_deposit,
            "deposit_amount": float(service.deposit_amount) if service.deposit_amount else None,
            "sort_order": service.sort_order,
            "color_code": service.color_code,
            
            # Business information
            "business_id": str(business.id),
            "business_name": business.name,
            "business_description": business.description,
            "business_phone": business.business_phone,
            "business_email": business.business_email,
            "logo_url": business.logo_url,
            "cover_image_url": business.cover_image_url,
            "booking_slug": business.booking_slug,
            "average_rating": float(business.average_rating) if business.average_rating else 0.0,
            "total_reviews": business.total_reviews,
            
            # Location
            "address": business.address,
            "city": business.city,
            "state": business.state,
            "postal_code": business.postal_code,
            "country": business.country,
            
            # Calculate distance if coordinates provided
            "distance_km": None
        }
        
        # Calculate distance if location search was used
        if latitude and longitude and business.location:
            from geoalchemy2 import func as geo_func
            from geoalchemy2.elements import WKTElement
            
            user_point = WKTElement(f'POINT({longitude} {latitude})', srid=4326)
            distance = db.query(
                geo_func.ST_Distance(Business.location, user_point)
            ).filter(Business.id == business.id).scalar()
            
            if distance:
                service_dict["distance_km"] = round(distance / 1000, 2)
        
        services_with_business.append(service_dict)
    
    return services_with_business


@router.get("/popular", response_model=List[dict])
async def get_popular_services(
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by business category"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get popular/most booked services.
    
    Returns services sorted by total number of appointments.
    Public endpoint.
    """
    from app.models.appointments import Appointment
    
    # Build query with appointment count
    query_builder = (
        db.query(
            Service,
            Business,
            func.count(Appointment.id).label('appointment_count')
        )
        .join(Business, Service.business_id == Business.id)
        .outerjoin(Appointment, Service.id == Appointment.service_id)
        .filter(
            Service.is_active == True,
            Business.is_active == True,
            Business.is_approved == True
        )
        .group_by(Service.id, Business.id)
    )
    
    # Category filter
    if category_id:
        query_builder = query_builder.filter(Business.category_id == category_id)
    
    # Order by appointment count
    results = query_builder.order_by(func.count(Appointment.id).desc()).limit(limit).all()
    
    # Format response
    popular_services = []
    for service, business, appointment_count in results:
        popular_services.append({
            "service_id": str(service.id),
            "service_name": service.name,
            "service_description": service.description,
            "price": float(service.price) if service.price else None,
            "duration_minutes": service.duration_minutes,
            "service_image_url": service.service_image_url,
            "business_id": str(business.id),
            "business_name": business.name,
            "logo_url": business.logo_url,
            "average_rating": float(business.average_rating) if business.average_rating else 0.0,
            "total_bookings": appointment_count
        })
    
    return popular_services


@router.get("/{service_id}/details", response_model=dict)
async def get_service_details(
    service_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific service.
    
    Includes service details and complete business information.
    Public endpoint.
    """
    # Get service with business
    result = (
        db.query(Service, Business)
        .join(Business, Service.business_id == Business.id)
        .filter(
            Service.id == service_id,
            Service.is_active == True
        )
        .first()
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service, business = result
    
    return {
        # Service information
        "service_id": str(service.id),
        "service_name": service.name,
        "service_description": service.description,
        "duration_minutes": service.duration_minutes,
        "price": float(service.price) if service.price else None,
        "service_image_url": service.service_image_url,
        "requires_deposit": service.requires_deposit,
        "deposit_amount": float(service.deposit_amount) if service.deposit_amount else None,
        "max_advance_days": service.max_advance_days,
        "min_advance_hours": service.min_advance_hours,
        "color_code": service.color_code,
        
        # Business information
        "business": {
            "business_id": str(business.id),
            "business_name": business.name,
            "business_description": business.description,
            "business_phone": business.business_phone,
            "business_email": business.business_email,
            "website": business.website,
            "logo_url": business.logo_url,
            "cover_image_url": business.cover_image_url,
            "booking_slug": business.booking_slug,
            "average_rating": float(business.average_rating) if business.average_rating else 0.0,
            "total_reviews": business.total_reviews,
            "address": business.address,
            "city": business.city,
            "state": business.state,
            "postal_code": business.postal_code,
            "country": business.country,
            "timezone": business.timezone
        }
    }

