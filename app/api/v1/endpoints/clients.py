"""
Client API endpoints for the Bookora application.

This module handles client registration, profile management, and other client-specific operations.
Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.clients import Client
from app.schemas.clients import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter()


# Client Registration and Management
@router.post("/register", response_model=ClientResponse)
async def register_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db)
):
    """Register a new client with Firebase UID."""
    
    # Check if client already exists
    existing_client = db.query(Client).filter(
        Client.firebase_uid == client_data.firebase_uid
    ).first()
    
    if existing_client:
        raise HTTPException(
            status_code=400,
            detail="Client with this Firebase UID already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Client).filter(Client.email == client_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Check if phone already exists (if provided)
    if client_data.phone_number:
        existing_phone = db.query(Client).filter(Client.phone_number == client_data.phone_number).first()
        if existing_phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number already registered"
            )
    
    # Create new client
    db_client = Client(
        firebase_uid=client_data.firebase_uid,
        email=client_data.email,
        first_name=client_data.first_name,
        last_name=client_data.last_name,
        phone_number=client_data.phone_number,
        date_of_birth=client_data.date_of_birth,
        gender=client_data.gender,
        address=client_data.address,
        city=client_data.city,
        state=client_data.state,
        country=client_data.country,
        postal_code=client_data.postal_code,
        latitude=client_data.latitude,
        longitude=client_data.longitude,
        profile_image_url=client_data.profile_image_url,
        fcm_token=client_data.fcm_token,
        email_verified=False,  # Will be verified by Firebase on frontend
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    
    return db_client


@router.get("/profile", response_model=ClientResponse)
async def get_client_profile(
    firebase_uid: str = Query(..., description="Firebase UID of the client"),
    db: Session = Depends(get_db)
):
    """Get client profile by Firebase UID."""
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client


@router.put("/profile", response_model=ClientResponse)
async def update_client_profile(
    client_update: ClientUpdate,
    firebase_uid: str = Query(..., description="Firebase UID of the client"),
    db: Session = Depends(get_db)
):
    """Update client profile."""
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Update client fields
    update_data = client_update.model_dump(exclude_unset=True)
    
    # Check for email conflicts if email is being updated
    if "email" in update_data and update_data["email"] != client.email:
        existing_email = db.query(Client).filter(
            Client.email == update_data["email"],
            Client.id != client.id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check for phone conflicts if phone is being updated
    if "phone_number" in update_data and update_data["phone_number"] != client.phone_number:
        existing_phone = db.query(Client).filter(
            Client.phone_number == update_data["phone_number"],
            Client.id != client.id
        ).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Apply updates
    for field, value in update_data.items():
        setattr(client, field, value)
    
    client.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(client)
    
    return client


@router.delete("/profile")
async def delete_client_profile(
    firebase_uid: str = Query(..., description="Firebase UID of the client"),
    db: Session = Depends(get_db)
):
    """Delete client profile."""
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    
    return {"message": "Client profile deleted successfully"}


@router.put("/fcm-token")
async def update_fcm_token(
    fcm_token: str,
    firebase_uid: str = Query(..., description="Firebase UID of the client"),
    db: Session = Depends(get_db)
):
    """Update FCM token for push notifications."""
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.fcm_token = fcm_token
    client.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "FCM token updated successfully"}


# Public endpoints (no authentication required)
@router.get("/search", response_model=List[ClientResponse])
async def search_clients(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """Search clients by name or email (public endpoint for businesses)."""
    
    search_filter = func.lower(func.concat(Client.first_name, " ", Client.last_name)).contains(query.lower())
    
    clients = db.query(Client).filter(
        search_filter,
        Client.is_active == True
    ).offset(skip).limit(limit).all()
    
    return clients


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_by_id(
    client_id: uuid.UUID = Path(..., description="Client ID"),
    db: Session = Depends(get_db)
):
    """Get client by ID (public endpoint for businesses)."""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_active == True
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client