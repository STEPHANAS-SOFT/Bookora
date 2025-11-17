"""
Communications API endpoints for the Bookora application.

This module handles chat room creation and messaging functionality
between clients and businesses.

Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.communications import ChatRoom, ChatMessage, MessageType
from app.models.clients import Client
from app.models.businesses import Business
from app.schemas.communications import (
    ChatRoomResponse, 
    ChatMessageResponse, 
    ChatRoomCreate, 
    ChatMessageCreate
)

router = APIRouter()


@router.get("/chat-rooms", response_model=List[ChatRoomResponse])
async def get_chat_rooms(
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get all chat rooms for current user.
    
    Returns list of chat rooms for client or business based on their Firebase UID.
    """
    # Check if user is client or business
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
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
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get messages for a chat room.
    
    Returns paginated list of messages in a specific chat room.
    """
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Verify user has access to this room
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
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
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return messages


@router.post("/chat-rooms", response_model=ChatRoomResponse)
async def create_chat_room(
    room_data: ChatRoomCreate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Create or get existing chat room between client and business.
    
    If a chat room already exists between the client and business,
    returns the existing room. Otherwise creates a new one.
    """
    # Get current client
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
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
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Send a message in a chat room.
    
    Creates a new message in the specified chat room from the authenticated user.
    """
    # Verify chat room exists
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Check if user has access to this room
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    is_from_client = False
    
    if client and room.client_id == client.id:
        is_from_client = True
    elif business and room.business_id == business.id:
        is_from_client = False
    else:
        raise HTTPException(status_code=403, detail="Access denied to chat room")
    
    # Create message
    message = ChatMessage(
        chat_room_id=room_id,
        sender_firebase_uid=firebase_uid,
        is_from_client=is_from_client,
        message_type=message_data.message_type or MessageType.TEXT,
        content=message_data.content,
        file_url=message_data.file_url,
        file_name=message_data.file_name
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
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Mark a message as read.
    
    Updates the read status of a message for the authenticated user.
    """
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
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if client and room.client_id == client.id:
        message.read_by_client = True
        message.read_at_client = func.now()
        # Decrease unread count
        if room.client_unread_count > 0:
            room.client_unread_count -= 1
    elif business and room.business_id == business.id:
        message.read_by_business = True
        message.read_at_business = func.now()
        # Decrease unread count
        if room.business_unread_count > 0:
            room.business_unread_count -= 1
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.commit()
    
    return {"status": "success", "message": "Message marked as read"}


@router.put("/chat-rooms/{room_id}/mark-all-read")
async def mark_all_messages_read(
    room_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Mark all messages in a chat room as read.
    
    Updates all unread messages in the room for the authenticated user.
    """
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Check user access
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if client and room.client_id == client.id:
        room.mark_read_by_client()
    elif business and room.business_id == business.id:
        room.mark_read_by_business()
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.commit()
    
    return {"status": "success", "message": "All messages marked as read"}
