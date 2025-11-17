"""
Favorite Business API endpoints for the Bookora application.

This module handles client favorite businesses, bookmarking, and
organizing businesses into collections.

Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.favorites import FavoriteBusiness, BusinessCollection, BusinessCollectionItem
from app.models.clients import Client
from app.models.businesses import Business
from app.schemas.favorites import (
    FavoriteBusinessCreate, FavoriteBusinessUpdate, FavoriteBusinessResponse,
    FavoriteBusinessListResponse, BusinessCollectionCreate, BusinessCollectionUpdate,
    BusinessCollectionResponse, BusinessCollectionItemCreate, BusinessCollectionItemUpdate,
    BusinessCollectionItemResponse, CollectionWithBusinessesResponse
)

router = APIRouter()


# Favorite Businesses
@router.get("/", response_model=FavoriteBusinessListResponse)
async def get_favorite_businesses(
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all favorite businesses for the current client.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get favorites
    query = db.query(FavoriteBusiness).filter(FavoriteBusiness.client_id == client.id)
    
    total = query.count()
    
    favorites = (
        query.order_by(desc(FavoriteBusiness.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return FavoriteBusinessListResponse(
        favorites=favorites,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=FavoriteBusinessResponse)
async def add_favorite_business(
    favorite_data: FavoriteBusinessCreate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Add a business to favorites.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Verify business exists
    business = db.query(Business).filter(Business.id == favorite_data.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if already favorited
    existing_favorite = db.query(FavoriteBusiness).filter(
        FavoriteBusiness.client_id == client.id,
        FavoriteBusiness.business_id == favorite_data.business_id
    ).first()
    
    if existing_favorite:
        raise HTTPException(status_code=400, detail="Business already in favorites")
    
    # Create favorite
    favorite = FavoriteBusiness(
        client_id=client.id,
        business_id=favorite_data.business_id,
        notes=favorite_data.notes,
        notify_on_availability=favorite_data.notify_on_availability,
        notify_on_promotions=favorite_data.notify_on_promotions
    )
    
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    return favorite


@router.put("/{favorite_id}", response_model=FavoriteBusinessResponse)
async def update_favorite_business(
    favorite_id: uuid.UUID,
    favorite_update: FavoriteBusinessUpdate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update favorite business settings.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get favorite
    favorite = db.query(FavoriteBusiness).filter(
        FavoriteBusiness.id == favorite_id,
        FavoriteBusiness.client_id == client.id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    # Update fields
    update_data = favorite_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(favorite, field, value)
    
    favorite.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(favorite)
    
    return favorite


@router.delete("/{favorite_id}")
async def remove_favorite_business(
    favorite_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Remove a business from favorites.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get and delete favorite
    favorite = db.query(FavoriteBusiness).filter(
        FavoriteBusiness.id == favorite_id,
        FavoriteBusiness.client_id == client.id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "Business removed from favorites"}


# Business Collections
@router.get("/collections", response_model=List[BusinessCollectionResponse])
async def get_collections(
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get all business collections for the current client.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get collections
    collections = (
        db.query(BusinessCollection)
        .filter(BusinessCollection.client_id == client.id)
        .order_by(desc(BusinessCollection.created_at))
        .all()
    )
    
    return collections


@router.post("/collections", response_model=BusinessCollectionResponse)
async def create_collection(
    collection_data: BusinessCollectionCreate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Create a new business collection.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Create collection
    collection = BusinessCollection(
        client_id=client.id,
        **collection_data.model_dump()
    )
    
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    return collection


@router.get("/collections/{collection_id}", response_model=CollectionWithBusinessesResponse)
async def get_collection_with_businesses(
    collection_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get a collection with all its businesses.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get collection
    collection = db.query(BusinessCollection).filter(
        BusinessCollection.id == collection_id,
        BusinessCollection.client_id == client.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get collection items
    items = (
        db.query(BusinessCollectionItem)
        .filter(BusinessCollectionItem.collection_id == collection_id)
        .order_by(BusinessCollectionItem.sort_order)
        .all()
    )
    
    return CollectionWithBusinessesResponse(
        collection=collection,
        businesses=items
    )


@router.put("/collections/{collection_id}", response_model=BusinessCollectionResponse)
async def update_collection(
    collection_id: uuid.UUID,
    collection_update: BusinessCollectionUpdate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update a collection.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get collection
    collection = db.query(BusinessCollection).filter(
        BusinessCollection.id == collection_id,
        BusinessCollection.client_id == client.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Update fields
    update_data = collection_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)
    
    collection.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(collection)
    
    return collection


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Delete a collection and all its items.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get and delete collection
    collection = db.query(BusinessCollection).filter(
        BusinessCollection.id == collection_id,
        BusinessCollection.client_id == client.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    db.delete(collection)
    db.commit()
    
    return {"message": "Collection deleted successfully"}


# Collection Items
@router.post("/collections/{collection_id}/businesses", response_model=BusinessCollectionItemResponse)
async def add_business_to_collection(
    collection_id: uuid.UUID,
    item_data: BusinessCollectionItemCreate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Add a business to a collection.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Verify collection ownership
    collection = db.query(BusinessCollection).filter(
        BusinessCollection.id == collection_id,
        BusinessCollection.client_id == client.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Verify business exists
    business = db.query(Business).filter(Business.id == item_data.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if already in collection
    existing_item = db.query(BusinessCollectionItem).filter(
        BusinessCollectionItem.collection_id == collection_id,
        BusinessCollectionItem.business_id == item_data.business_id
    ).first()
    
    if existing_item:
        raise HTTPException(status_code=400, detail="Business already in this collection")
    
    # Create collection item
    item = BusinessCollectionItem(
        collection_id=collection_id,
        business_id=item_data.business_id,
        notes=item_data.notes,
        sort_order=item_data.sort_order or 0
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return item


@router.put("/collections/{collection_id}/businesses/{item_id}", response_model=BusinessCollectionItemResponse)
async def update_collection_item(
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    item_update: BusinessCollectionItemUpdate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update a business in a collection.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Verify collection ownership
    collection = db.query(BusinessCollection).filter(
        BusinessCollection.id == collection_id,
        BusinessCollection.client_id == client.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get item
    item = db.query(BusinessCollectionItem).filter(
        BusinessCollectionItem.id == item_id,
        BusinessCollectionItem.collection_id == collection_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in collection")
    
    # Update fields
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    return item


@router.delete("/collections/{collection_id}/businesses/{item_id}")
async def remove_business_from_collection(
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Remove a business from a collection.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Verify collection ownership
    collection = db.query(BusinessCollection).filter(
        BusinessCollection.id == collection_id,
        BusinessCollection.client_id == client.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get and delete item
    item = db.query(BusinessCollectionItem).filter(
        BusinessCollectionItem.id == item_id,
        BusinessCollectionItem.collection_id == collection_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in collection")
    
    db.delete(item)
    db.commit()
    
    return {"message": "Business removed from collection"}

