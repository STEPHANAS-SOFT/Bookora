"""
WebSocket Connection Manager for real-time chat functionality.

This module handles WebSocket connections for real-time messaging
between clients and businesses in the Bookora application.
"""

from typing import List, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat.
    
    Handles connection lifecycle, message broadcasting,
    and room-based messaging for client-business communication.
    """
    
    def __init__(self):
        # Store active connections by user Firebase UID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Store user rooms (chat rooms user is part of)
        self.user_rooms: Dict[str, Set[str]] = {}
        
        # Store room members (which users are in each room)
        self.room_members: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, firebase_uid: str):
        """
        Accept a WebSocket connection and add user to active connections.
        
        Args:
            websocket: The WebSocket connection
            firebase_uid: Firebase UID of the connecting user
        """
        await websocket.accept()
        self.active_connections[firebase_uid] = websocket
        
        # Initialize user rooms if not exists
        if firebase_uid not in self.user_rooms:
            self.user_rooms[firebase_uid] = set()
        
        logger.info(f"User {firebase_uid} connected via WebSocket")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_confirmed",
            "message": "Connected to Bookora chat",
            "timestamp": datetime.now().isoformat()
        }, firebase_uid)
    
    async def disconnect(self, firebase_uid: str):
        """
        Remove user from active connections and clean up rooms.
        
        Args:
            firebase_uid: Firebase UID of the disconnecting user
        """
        if firebase_uid in self.active_connections:
            del self.active_connections[firebase_uid]
        
        # Remove user from all rooms
        if firebase_uid in self.user_rooms:
            for room_id in self.user_rooms[firebase_uid].copy():
                await self.leave_room(firebase_uid, room_id)
            del self.user_rooms[firebase_uid]
        
        logger.info(f"User {firebase_uid} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, firebase_uid: str):
        """
        Send a message to a specific user.
        
        Args:
            message: Message data to send
            firebase_uid: Target user's Firebase UID
        """
        if firebase_uid in self.active_connections:
            try:
                websocket = self.active_connections[firebase_uid]
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Error sending message to {firebase_uid}: {e}")
                # Remove broken connection
                await self.disconnect(firebase_uid)
                return False
        return False
    
    async def join_room(self, firebase_uid: str, room_id: str):
        """
        Add user to a chat room.
        
        Args:
            firebase_uid: User's Firebase UID
            room_id: Chat room ID
        """
        # Add room to user's rooms
        if firebase_uid not in self.user_rooms:
            self.user_rooms[firebase_uid] = set()
        self.user_rooms[firebase_uid].add(room_id)
        
        # Add user to room members
        if room_id not in self.room_members:
            self.room_members[room_id] = set()
        self.room_members[room_id].add(firebase_uid)
        
        logger.info(f"User {firebase_uid} joined room {room_id}")
        
        # Notify user of successful room join
        await self.send_personal_message({
            "type": "room_joined",
            "room_id": room_id,
            "timestamp": datetime.now().isoformat()
        }, firebase_uid)
    
    async def leave_room(self, firebase_uid: str, room_id: str):
        """
        Remove user from a chat room.
        
        Args:
            firebase_uid: User's Firebase UID
            room_id: Chat room ID
        """
        # Remove room from user's rooms
        if firebase_uid in self.user_rooms:
            self.user_rooms[firebase_uid].discard(room_id)
        
        # Remove user from room members
        if room_id in self.room_members:
            self.room_members[room_id].discard(firebase_uid)
            
            # Clean up empty room
            if not self.room_members[room_id]:
                del self.room_members[room_id]
        
        logger.info(f"User {firebase_uid} left room {room_id}")
    
    async def broadcast_to_room(self, message: dict, room_id: str, exclude_user: str = None):
        """
        Broadcast a message to all users in a room.
        
        Args:
            message: Message data to broadcast
            room_id: Target chat room ID
            exclude_user: Firebase UID to exclude from broadcast (optional)
        """
        if room_id not in self.room_members:
            return
        
        successful_sends = 0
        failed_sends = []
        
        for firebase_uid in self.room_members[room_id].copy():
            if exclude_user and firebase_uid == exclude_user:
                continue
            
            success = await self.send_personal_message(message, firebase_uid)
            if success:
                successful_sends += 1
            else:
                failed_sends.append(firebase_uid)
        
        logger.info(f"Broadcast to room {room_id}: {successful_sends} successful, {len(failed_sends)} failed")
        
        return {
            "successful_sends": successful_sends,
            "failed_sends": failed_sends
        }
    
    async def send_chat_message(self, message_data: dict, room_id: str, sender_uid: str):
        """
        Send a chat message to a room and broadcast to members.
        
        Args:
            message_data: Chat message data
            room_id: Target chat room ID
            sender_uid: Sender's Firebase UID
        """
        # Prepare message for broadcast
        broadcast_message = {
            "type": "chat_message",
            "room_id": room_id,
            "sender_uid": sender_uid,
            "message": message_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Broadcast to all room members except sender
        result = await self.broadcast_to_room(broadcast_message, room_id, exclude_user=sender_uid)
        
        # Send confirmation to sender
        await self.send_personal_message({
            "type": "message_sent",
            "room_id": room_id,
            "message_id": message_data.get("id"),
            "timestamp": datetime.now().isoformat()
        }, sender_uid)
        
        return result
    
    async def send_typing_indicator(self, room_id: str, sender_uid: str, is_typing: bool):
        """
        Send typing indicator to room members.
        
        Args:
            room_id: Target chat room ID
            sender_uid: User who is typing
            is_typing: Whether user is currently typing
        """
        typing_message = {
            "type": "typing_indicator",
            "room_id": room_id,
            "sender_uid": sender_uid,
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast_to_room(typing_message, room_id, exclude_user=sender_uid)
    
    async def send_appointment_notification(self, appointment_data: dict, recipient_uids: List[str]):
        """
        Send appointment-related notifications to specific users.
        
        Args:
            appointment_data: Appointment notification data
            recipient_uids: List of Firebase UIDs to notify
        """
        notification = {
            "type": "appointment_notification",
            "appointment": appointment_data,
            "timestamp": datetime.now().isoformat()
        }
        
        successful_sends = 0
        failed_sends = []
        
        for firebase_uid in recipient_uids:
            success = await self.send_personal_message(notification, firebase_uid)
            if success:
                successful_sends += 1
            else:
                failed_sends.append(firebase_uid)
        
        return {
            "successful_sends": successful_sends,
            "failed_sends": failed_sends
        }
    
    def get_active_users(self) -> List[str]:
        """Get list of currently connected users."""
        return list(self.active_connections.keys())
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Get list of users in a specific room."""
        return list(self.room_members.get(room_id, set()))
    
    def is_user_online(self, firebase_uid: str) -> bool:
        """Check if a user is currently connected."""
        return firebase_uid in self.active_connections
    
    def get_user_rooms(self, firebase_uid: str) -> List[str]:
        """Get list of rooms a user is part of."""
        return list(self.user_rooms.get(firebase_uid, set()))


# Global connection manager instance
connection_manager = ConnectionManager()