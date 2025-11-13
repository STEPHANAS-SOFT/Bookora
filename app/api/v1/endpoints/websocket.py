"""
WebSocket endpoints for real-time chat functionality.

This module handles WebSocket connections and real-time messaging
between clients and businesses.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import json
import logging
from typing import Optional

from app.core.database import get_db
from app.websocket.connection_manager import connection_manager
from app.models.communications import ChatRoom, ChatMessage, MessageType
from app.models.clients import Client
from app.models.businesses import Business

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_chat_room(room_id: str, db: Session):
    """Get chat room and validate access."""
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    return chat_room


@router.websocket("/chat/{firebase_uid}")
async def websocket_endpoint(
    websocket: WebSocket,
    firebase_uid: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat.
    
    Handles connection management and message routing for
    client-business communication.
    """
    try:
        # Accept connection and add to manager
        await connection_manager.connect(websocket, firebase_uid)
        
        # Verify user exists (either client or business)
        user = (db.query(Client).filter(Client.firebase_uid == firebase_uid).first() or
                db.query(Business).filter(Business.firebase_uid == firebase_uid).first())
        
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return
        
        # Join user's active chat rooms
        if isinstance(user, Client):
            chat_rooms = db.query(ChatRoom).filter(ChatRoom.client_id == user.id).all()
        else:  # Business
            chat_rooms = db.query(ChatRoom).filter(ChatRoom.business_id == user.id).all()
        
        for room in chat_rooms:
            await connection_manager.join_room(firebase_uid, str(room.id))
        
        # Listen for messages
        while True:
            try:
                # Receive message from WebSocket
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(message_data, firebase_uid, db)
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, firebase_uid)
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(firebase_uid)
        logger.info(f"WebSocket disconnected: {firebase_uid}")
    except Exception as e:
        logger.error(f"WebSocket error for user {firebase_uid}: {e}")
        await connection_manager.disconnect(firebase_uid)


async def handle_websocket_message(message_data: dict, firebase_uid: str, db: Session):
    """
    Handle incoming WebSocket messages.
    
    Routes messages based on type and performs appropriate actions.
    """
    message_type = message_data.get("type")
    
    if message_type == "send_message":
        await handle_send_message(message_data, firebase_uid, db)
    elif message_type == "join_room":
        await handle_join_room(message_data, firebase_uid, db)
    elif message_type == "leave_room":
        await handle_leave_room(message_data, firebase_uid, db)
    elif message_type == "typing":
        await handle_typing_indicator(message_data, firebase_uid, db)
    elif message_type == "mark_read":
        await handle_mark_read(message_data, firebase_uid, db)
    else:
        await connection_manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }, firebase_uid)


async def handle_send_message(message_data: dict, firebase_uid: str, db: Session):
    """Handle sending a chat message."""
    try:
        room_id = message_data.get("room_id")
        content = message_data.get("content")
        msg_type = message_data.get("message_type", MessageType.TEXT)
        
        if not room_id or not content:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "Missing room_id or content"
            }, firebase_uid)
            return
        
        # Get chat room and validate access
        chat_room = await get_chat_room(room_id, db)
        
        # Verify user is part of this chat room
        user = (db.query(Client).filter(Client.firebase_uid == firebase_uid).first() or
                db.query(Business).filter(Business.firebase_uid == firebase_uid).first())
        
        if not user:
            return
        
        is_from_client = isinstance(user, Client)
        
        # Verify access to chat room
        if ((is_from_client and chat_room.client_id != user.id) or 
            (not is_from_client and chat_room.business_id != user.id)):
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "Access denied to chat room"
            }, firebase_uid)
            return
        
        # Create new chat message
        new_message = ChatMessage(
            chat_room_id=room_id,
            sender_firebase_uid=firebase_uid,
            is_from_client=is_from_client,
            message_type=msg_type,
            content=content,
            file_url=message_data.get("file_url"),
            file_name=message_data.get("file_name"),
            file_size=message_data.get("file_size"),
            file_mime_type=message_data.get("file_mime_type")
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        # Update chat room
        chat_room.last_message_at = new_message.created_at
        if is_from_client:
            chat_room.business_unread_count += 1
        else:
            chat_room.client_unread_count += 1
        
        db.commit()
        
        # Broadcast message to room
        await connection_manager.send_chat_message({
            "id": str(new_message.id),
            "content": content,
            "message_type": msg_type,
            "file_url": message_data.get("file_url"),
            "sender_name": user.full_name if is_from_client else user.name,
            "created_at": new_message.created_at.isoformat()
        }, room_id, firebase_uid)
        
    except Exception as e:
        logger.error(f"Error handling send_message: {e}")
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Failed to send message"
        }, firebase_uid)


async def handle_join_room(message_data: dict, firebase_uid: str, db: Session):
    """Handle joining a chat room."""
    room_id = message_data.get("room_id")
    if room_id:
        await connection_manager.join_room(firebase_uid, room_id)


async def handle_leave_room(message_data: dict, firebase_uid: str, db: Session):
    """Handle leaving a chat room."""
    room_id = message_data.get("room_id")
    if room_id:
        await connection_manager.leave_room(firebase_uid, room_id)


async def handle_typing_indicator(message_data: dict, firebase_uid: str, db: Session):
    """Handle typing indicator."""
    room_id = message_data.get("room_id")
    is_typing = message_data.get("is_typing", False)
    
    if room_id:
        await connection_manager.send_typing_indicator(room_id, firebase_uid, is_typing)


async def handle_mark_read(message_data: dict, firebase_uid: str, db: Session):
    """Handle marking messages as read."""
    try:
        room_id = message_data.get("room_id")
        
        if not room_id:
            return
        
        # Get chat room
        chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not chat_room:
            return
        
        # Determine if user is client or business
        user = (db.query(Client).filter(Client.firebase_uid == firebase_uid).first() or
                db.query(Business).filter(Business.firebase_uid == firebase_uid).first())
        
        if not user:
            return
        
        is_client = isinstance(user, Client)
        
        # Mark messages as read
        if is_client:
            chat_room.mark_read_by_client()
        else:
            chat_room.mark_read_by_business()
        
        db.commit()
        
        # Notify sender that messages were read
        await connection_manager.send_personal_message({
            "type": "messages_read",
            "room_id": room_id
        }, firebase_uid)
        
    except Exception as e:
        logger.error(f"Error handling mark_read: {e}")


@router.get("/active-users")
async def get_active_users():
    """Get list of currently connected users."""
    return {
        "active_users": connection_manager.get_active_users(),
        "total_connected": len(connection_manager.get_active_users())
    }


@router.get("/room/{room_id}/members")
async def get_room_members(room_id: str):
    """Get members of a specific chat room."""
    return {
        "room_id": room_id,
        "members": connection_manager.get_room_members(room_id),
        "total_members": len(connection_manager.get_room_members(room_id))
    }