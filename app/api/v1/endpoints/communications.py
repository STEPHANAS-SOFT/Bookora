"""
Communication API endpoints for chat functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.communications import ChatRoom, ChatMessage
from app.models.clients import Client
from app.models.businesses import Business
from app.schemas.communications import (
    ChatRoomResponse, 
    ChatMessageResponse, 
    ChatRoomCreate, 
    ChatMessageCreate
)
from app.core.auth import get_current_firebase_user

router = APIRouter()

@router.get("/chat-rooms", response_model=List[ChatRoomResponse])
async def get_chat_rooms(
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get all chat rooms for current user."""
    # Check if user is client or business
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client:
        rooms = db.query(ChatRoom).filter(ChatRoom.client_id == client.id).all()
    elif business:
        rooms = db.query(ChatRoom).filter(ChatRoom.business_id == business.id).all()
    else:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    return rooms

@router.get("/chat-rooms/{room_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    room_id: uuid.UUID,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get messages for a chat room."""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Verify user has access to this room
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    has_access = False
    if client and room.client_id == client.id:
        has_access = True
    elif business and room.business_id == business.id:
        has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied to chat room")
    
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_room_id == room_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    
    return messages


@router.post("/chat-rooms", response_model=ChatRoomResponse)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Create or get existing chat room between client and business."""
    # Get current client
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Verify business exists
    business = db.query(Business).filter(Business.id == room_data.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if chat room already exists
    existing_room = (
        db.query(ChatRoom)
        .filter(
            ChatRoom.client_id == client.id,
            ChatRoom.business_id == room_data.business_id
        )
        .first()
    )
    
    if existing_room:
        return existing_room
    
    # Create new chat room
    chat_room = ChatRoom(
        client_id=client.id,
        business_id=room_data.business_id
    )
    
    db.add(chat_room)
    db.commit()
    db.refresh(chat_room)
    
    return chat_room


@router.post("/chat-rooms/{room_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    room_id: uuid.UUID,
    message_data: ChatMessageCreate,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Send a message in a chat room."""
    # Verify chat room exists
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Check if user has access to this room
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    is_from_client = False
    sender_name = ""
    
    if client and room.client_id == client.id:
        is_from_client = True
        sender_name = client.full_name
    elif business and room.business_id == business.id:
        is_from_client = False
        sender_name = business.name
    else:
        raise HTTPException(status_code=403, detail="Access denied to chat room")
    
    # Create message
    message_dict = message_data.dict()
    message_dict.pop('chat_room_id', None)  # Remove from dict as we set it explicitly
    
    message = ChatMessage(
        chat_room_id=room_id,
        sender_firebase_uid=current_user["uid"],
        sender_name=sender_name,
        is_from_client=is_from_client,
        **message_dict
    )
    
    db.add(message)
    
    # Update room's last message timestamp
    room.last_message_at = func.now()
    
    # Update unread counts
    if is_from_client:
        room.business_unread_count = (room.business_unread_count or 0) + 1
    else:
        room.client_unread_count = (room.client_unread_count or 0) + 1
    
    db.commit()
    db.refresh(message)
    
    return message


@router.put("/chat-rooms/{room_id}/messages/{message_id}/read")
async def mark_message_as_read(
    room_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Mark a message as read."""
    # Verify access to room and message
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    message = (
        db.query(ChatMessage)
        .filter(ChatMessage.id == message_id, ChatMessage.chat_room_id == room_id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check user access and update read status
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client and room.client_id == client.id:
        message.read_by_client = True
        message.read_at_client = func.now()
    elif business and room.business_id == business.id:
        message.read_by_business = True
        message.read_at_business = func.now()
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.commit()
    
    return {"status": "success", "message": "Message marked as read"}


@router.get("/nearby-businesses", response_model=List[dict])
async def get_nearby_businesses(
    latitude: float = Query(..., ge=-90, le=90, description="Current latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Current longitude"), 
    radius_km: float = Query(10.0, ge=1.0, le=50.0, description="Search radius in kilometers"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by business category"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """
    Get businesses near the user's location.
    
    Returns businesses within the specified radius, ordered by distance.
    """
    from geoalchemy2 import func as geo_func
    from geoalchemy2.elements import WKTElement
    from app.models.businesses import Business, BusinessStatus
    
    # Create point for user location
    user_point = WKTElement(f'POINT({longitude} {latitude})', srid=4326)
    
    # Build query
    query_filter = (
        db.query(
            Business,
            geo_func.ST_Distance(Business.location, user_point).label('distance')
        )
        .filter(Business.status == BusinessStatus.ACTIVE)
        .filter(Business.location.isnot(None))
        .filter(
            geo_func.ST_DWithin(
                Business.location,
                user_point,
                radius_km * 1000  # Convert km to meters
            )
        )
    )
    
    # Apply category filter if provided
    if category_id:
        query_filter = query_filter.filter(Business.category_id == category_id)
    
    # Order by distance and apply limit
    results = (
        query_filter
        .order_by('distance')
        .limit(limit)
        .all()
    )
    
    # Format response with distance
    businesses_with_distance = []
    for business, distance in results:
        business_dict = {
            "id": str(business.id),
            "name": business.name,
            "description": business.description,
            "category_id": str(business.category_id),
            "address": business.address,
            "city": business.city,
            "latitude": business.latitude,
            "longitude": business.longitude,
            "business_phone": business.business_phone,
            "business_email": business.business_email,
            "booking_slug": business.booking_slug,
            "distance_km": round(distance / 1000, 2)  # Convert meters to km
        }
        businesses_with_distance.append(business_dict)
    
    return businesses_with_distance