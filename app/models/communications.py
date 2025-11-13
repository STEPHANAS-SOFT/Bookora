"""
Communication domain models for the Bookora application.

This module contains models for real-time chat functionality
between clients and businesses.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from datetime import datetime
import uuid

from app.models.base import BaseModel


class MessageType(str, Enum):
    """Enumeration for message types."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    APPOINTMENT_REQUEST = "appointment_request"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    SYSTEM = "system"


class ChatRoomStatus(str, Enum):
    """Enumeration for chat room status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class ChatRoom(BaseModel):
    """
    Model representing a chat room between a client and business.
    
    Each client-business pair has one chat room for all their
    communication and appointment-related messages.
    """
    __tablename__ = "chat_rooms"
    
    # Participants
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Room Details
    status = Column(SQLEnum(ChatRoomStatus), default=ChatRoomStatus.ACTIVE, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Unread Message Counts
    client_unread_count = Column(Integer, default=0, nullable=False)
    business_unread_count = Column(Integer, default=0, nullable=False)
    
    # Room Settings
    client_notifications_enabled = Column(Boolean, default=True, nullable=False)
    business_notifications_enabled = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    client = relationship("Client")
    business = relationship("Business")
    messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    
    @property
    def latest_message(self):
        """Get the latest message in this chat room."""
        if self.messages:
            return self.messages[-1]
        return None
    
    def mark_read_by_client(self):
        """Mark all messages as read by client."""
        self.client_unread_count = 0
        # Update all unread messages from business
        for message in self.messages:
            if not message.is_from_client and not message.read_by_client:
                message.read_by_client = True
                message.read_at_client = func.now()
    
    def mark_read_by_business(self):
        """Mark all messages as read by business."""
        self.business_unread_count = 0
        # Update all unread messages from client
        for message in self.messages:
            if message.is_from_client and not message.read_by_business:
                message.read_by_business = True
                message.read_at_business = func.now()
    
    def __repr__(self):
        return f"<ChatRoom(client={self.client.full_name if self.client else 'None'}, business={self.business.name if self.business else 'None'})>"


class ChatMessage(BaseModel):
    """
    Model representing individual messages in chat rooms.
    
    Supports text messages, images, files, and system messages
    for appointment-related notifications.
    """
    __tablename__ = "chat_messages"
    
    # Room and Sender
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_firebase_uid = Column(String(128), nullable=False, comment="Firebase UID of message sender")
    is_from_client = Column(Boolean, nullable=False, comment="True if sent by client, False if sent by business")
    
    # Message Content
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT, nullable=False)
    content = Column(Text, nullable=False)
    
    # File/Image Messages
    file_url = Column(String(500), nullable=True, comment="URL for image/file messages")
    file_name = Column(String(255), nullable=True, comment="Original file name")
    file_size = Column(Integer, nullable=True, comment="File size in bytes")
    file_mime_type = Column(String(100), nullable=True, comment="MIME type of the file")
    
    # Read Status
    read_by_client = Column(Boolean, default=False, nullable=False)
    read_by_business = Column(Boolean, default=False, nullable=False)
    read_at_client = Column(DateTime(timezone=True), nullable=True)
    read_at_business = Column(DateTime(timezone=True), nullable=True)
    
    # Message Status
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # System Messages (for appointments)
    related_appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    
    # Relationships
    chat_room = relationship("ChatRoom", back_populates="messages")
    related_appointment = relationship("Appointment")
    
    @property
    def is_read(self) -> bool:
        """Check if message has been read by the recipient."""
        if self.is_from_client:
            return self.read_by_business
        else:
            return self.read_by_client
    
    @property
    def sender_name(self) -> str:
        """Get the name of the message sender."""
        if self.is_from_client and self.chat_room.client:
            return self.chat_room.client.full_name
        elif not self.is_from_client and self.chat_room.business:
            return self.chat_room.business.name
        return "Unknown"
    
    def mark_as_read(self, reader_is_client: bool):
        """Mark message as read by the specified reader."""
        if reader_is_client:
            self.read_by_client = True
            self.read_at_client = func.now()
        else:
            self.read_by_business = True
            self.read_at_business = func.now()
    
    def edit_content(self, new_content: str):
        """Edit the message content."""
        self.content = new_content
        self.is_edited = True
        self.edited_at = func.now()
    
    def soft_delete(self):
        """Soft delete the message."""
        self.is_deleted = True
        self.deleted_at = func.now()
        self.content = "[Message deleted]"
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(sender={self.sender_name}, type={self.message_type}, content='{content_preview}')>"