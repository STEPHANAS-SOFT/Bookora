"""
Client API endpoints for the Bookora application.

This module contains all API endpoints related to client management,
including registration, profile management, and client preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.clients import Client
from app.schemas.clients import ClientCreate, ClientUpdate, ClientResponse
from app.core.auth import get_current_firebase_user

router = APIRouter()

# Client Registration and Management
@router.post("/register", response_model=ClientResponse)
async def register_client(
    client_data: ClientCreate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Register a new client."""
    # Check if user already exists
    existing_client = (
        db.query(Client)
        .filter(Client.firebase_uid == client_data.firebase_uid)
        .first()
    )
    
    if existing_client:
        raise HTTPException(
            status_code=400,
            detail="User already registered as client"
        )
    
    # Create client
    client_dict = client_data.dict()
    firebase_uid = client_dict.pop('firebase_uid')
    email = client_dict.pop('email')
    
    client = Client(
        firebase_uid=firebase_uid,
        email=email,
        email_verified=current_user.get("email_verified", False),
        **client_dict
    )
    
    # Set location if provided
    if client_data.latitude and client_data.longitude:
        client.set_location(client_data.latitude, client_data.longitude)
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    return client


@router.get("/me", response_model=ClientResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Get current client's profile."""
    client = (
        db.query(Client)
        .filter(Client.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client profile not found"
        )
    
    return client


@router.put("/me", response_model=ClientResponse)
async def update_my_profile(
    client_update: ClientUpdate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)

):
    """Update current client's profile."""
    client = (
        db.query(Client)
        .filter(Client.firebase_uid == current_user["uid"])
        .first()
    )
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client profile not found"
        )
    
    # Update fields
    update_data = client_update.dict(exclude_unset=True)
    
    # Handle location update
    if "latitude" in update_data and "longitude" in update_data:
        client.set_location(update_data.pop("latitude"), update_data.pop("longitude"))
    
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    
    return client


@router.get("/by-firebase-uid/{firebase_uid}", response_model=ClientResponse)
async def get_client_by_firebase_uid(
    firebase_uid: str = Path(..., description="Firebase UID"),
    db: Session = Depends(get_db)

):
    """Get client by Firebase UID."""
    client = (
        db.query(Client)
        .filter(Client.firebase_uid == firebase_uid)
        .first()
    )
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )
    
    return client


@router.put("/by-firebase-uid/{firebase_uid}", response_model=ClientResponse)
async def update_client_by_firebase_uid(
    client_data: ClientUpdate,
    firebase_uid: str = Path(..., description="Firebase UID"),
    db: Session = Depends(get_db)

):
    """Update client by Firebase UID."""
    client = (
        db.query(Client)
        .filter(Client.firebase_uid == firebase_uid)
        .first()
    )
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )
    
    # Update client fields
    update_data = client_data.dict(exclude_unset=True)
    
    # Handle location update
    if "latitude" in update_data and "longitude" in update_data:
        client.set_location(update_data.pop("latitude"), update_data.pop("longitude"))

    for field, value in update_data.items():
        if hasattr(client, field):
            setattr(client, field, value)
    
    client.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(client)
    
    return client


@router.delete("/by-firebase-uid/{firebase_uid}")
async def delete_client_by_firebase_uid(
    firebase_uid: str = Path(..., description="Firebase UID"),
    db: Session = Depends(get_db)

):
    """Delete client by Firebase UID (soft delete)."""
    client = (
        db.query(Client)
        .filter(Client.firebase_uid == firebase_uid)
        .first()
    )
    
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )
    
    # Soft delete - mark as inactive or delete based on your business logic
    client.is_active = False
    client.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Client successfully deactivated"}