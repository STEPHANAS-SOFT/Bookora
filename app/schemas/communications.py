"""
Pydantic schemas for communication-related API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.communications import MessageType, ChatRoomStatus


class ChatRoomCreate(BaseModel):
    """Schema for creating a new chat room."""
    business_id: uuid.UUID = Field(..., description="ID of the business to chat with")


class ChatMessageBase(BaseModel):
    """Base schema for chat message data."""
    content: str = Field(..., min_length=1, max_length=2000)
    message_type: MessageType = MessageType.TEXT


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message."""
    chat_room_id: uuid.UUID
    file_url: Optional[str] = Field(None, max_length=500)
    file_name: Optional[str] = Field(None, max_length=255)
    file_size: Optional[int] = Field(None, gt=0)
    file_mime_type: Optional[str] = Field(None, max_length=100)


class ChatMessageResponse(BaseModel):
    """Response schema for chat message data."""
    id: uuid.UUID
    chat_room_id: uuid.UUID
    sender_firebase_uid: str
    sender_name: str
    is_from_client: bool
    
    # Message content
    message_type: MessageType
    content: str
    file_url: Optional[str]
    file_name: Optional[str]
    file_size: Optional[int]
    file_mime_type: Optional[str]
    
    # Read status
    read_by_client: bool
    read_by_business: bool
    read_at_client: Optional[datetime]
    read_at_business: Optional[datetime]
    is_read: bool
    
    # Message status
    is_edited: bool
    edited_at: Optional[datetime]
    is_deleted: bool
    deleted_at: Optional[datetime]
    
    # Related appointment
    related_appointment_id: Optional[uuid.UUID]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ChatRoomResponse(BaseModel):
    """Response schema for chat room data."""
    id: uuid.UUID
    client_id: uuid.UUID
    business_id: uuid.UUID
    status: ChatRoomStatus
    
    # Room details
    last_message_at: Optional[datetime]
    client_unread_count: int
    business_unread_count: int
    
    # Settings
    client_notifications_enabled: bool
    business_notifications_enabled: bool
    
    # Latest message
    latest_message: Optional[ChatMessageResponse]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}