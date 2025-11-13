"""
Firebase Cloud Messaging (FCM) HTTP v1 API Service
Handles push notifications using the modern FCM API with service account authentication
"""

import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FCMMessage(BaseModel):
    """FCM message structure for HTTP v1 API"""
    token: str  # Device FCM token
    title: str
    body: str
    data: Optional[Dict[str, str]] = None
    image_url: Optional[str] = None
    click_action: Optional[str] = None


class FCMService:
    """Firebase Cloud Messaging service using HTTP v1 API"""
    
    def __init__(self):
        self.project_id = settings.FCM_PROJECT_ID or settings.FIREBASE_PROJECT_ID
        self.fcm_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        self.credentials = None
        self._initialize_credentials()
    
    def _initialize_credentials(self) -> None:
        """Initialize Firebase service account credentials"""
        try:
            # Use Firebase service account credentials for FCM
            firebase_credentials = settings.firebase_service_account_info
            self.credentials = service_account.Credentials.from_service_account_info(
                firebase_credentials,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            logger.info("FCM service initialized with Firebase credentials")
        except Exception as e:
            logger.error(f"Failed to initialize FCM credentials: {e}")
            raise
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token for FCM API"""
        try:
            # Refresh token if needed
            if not self.credentials.valid:
                self.credentials.refresh(Request())
            
            return self.credentials.token
        except Exception as e:
            logger.error(f"Failed to get FCM access token: {e}")
            raise
    
    async def send_notification(self, message: FCMMessage) -> bool:
        """
        Send FCM notification to a single device
        
        Args:
            message: FCM message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare FCM payload
            payload = {
                "message": {
                    "token": message.token,
                    "notification": {
                        "title": message.title,
                        "body": message.body
                    }
                }
            }
            
            # Add optional fields
            if message.image_url:
                payload["message"]["notification"]["image"] = message.image_url
            
            if message.data:
                payload["message"]["data"] = message.data
            
            if message.click_action:
                payload["message"]["android"] = {
                    "notification": {
                        "click_action": message.click_action
                    }
                }
                payload["message"]["apns"] = {
                    "payload": {
                        "aps": {
                            "category": message.click_action
                        }
                    }
                }
            
            # Get access token
            access_token = self._get_access_token()
            
            # Send request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
            
            if response.status_code == 200:
                logger.info(f"FCM notification sent successfully to token: {message.token[:20]}...")
                return True
            else:
                logger.error(f"FCM notification failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending FCM notification: {e}")
            return False
    
    async def send_bulk_notifications(self, messages: List[FCMMessage]) -> Dict[str, int]:
        """
        Send FCM notifications to multiple devices
        
        Args:
            messages: List of FCM messages to send
            
        Returns:
            Dict with success and failure counts
        """
        results = {"success": 0, "failed": 0}
        
        for message in messages:
            success = await self.send_notification(message)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"Bulk FCM notifications: {results['success']} sent, {results['failed']} failed")
        return results
    
    async def send_topic_notification(
        self, 
        topic: str, 
        title: str, 
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send FCM notification to a topic
        
        Args:
            topic: FCM topic name
            title: Notification title
            body: Notification body
            data: Additional data payload
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = {
                "message": {
                    "topic": topic,
                    "notification": {
                        "title": title,
                        "body": body
                    }
                }
            }
            
            if data:
                payload["message"]["data"] = data
            
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
            
            if response.status_code == 200:
                logger.info(f"FCM topic notification sent successfully to: {topic}")
                return True
            else:
                logger.error(f"FCM topic notification failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending FCM topic notification: {e}")
            return False


# Global FCM service instance
fcm_service = FCMService()


# Helper functions for common notification types
async def send_appointment_notification(
    fcm_token: str,
    business_name: str,
    appointment_date: str,
    notification_type: str = "reminder"
) -> bool:
    """Send appointment-related notification"""
    
    if notification_type == "reminder":
        title = "Appointment Reminder"
        body = f"Your appointment with {business_name} is scheduled for {appointment_date}"
    elif notification_type == "confirmed":
        title = "Appointment Confirmed"
        body = f"Your appointment with {business_name} has been confirmed for {appointment_date}"
    elif notification_type == "cancelled":
        title = "Appointment Cancelled"
        body = f"Your appointment with {business_name} on {appointment_date} has been cancelled"
    else:
        title = "Appointment Update"
        body = f"Update regarding your appointment with {business_name}"
    
    message = FCMMessage(
        token=fcm_token,
        title=title,
        body=body,
        data={
            "type": "appointment",
            "action": notification_type,
            "business_name": business_name,
            "appointment_date": appointment_date
        },
        click_action="APPOINTMENT_DETAILS"
    )
    
    return await fcm_service.send_notification(message)


async def send_chat_notification(
    fcm_token: str,
    sender_name: str,
    message_preview: str
) -> bool:
    """Send new chat message notification"""
    
    message = FCMMessage(
        token=fcm_token,
        title=f"New message from {sender_name}",
        body=message_preview,
        data={
            "type": "chat",
            "sender_name": sender_name
        },
        click_action="CHAT_ROOM"
    )
    
    return await fcm_service.send_notification(message)


async def send_business_notification(
    fcm_token: str,
    title: str,
    body: str,
    notification_type: str = "general"
) -> bool:
    """Send business-related notification"""
    
    message = FCMMessage(
        token=fcm_token,
        title=title,
        body=body,
        data={
            "type": "business",
            "action": notification_type
        }
    )
    
    return await fcm_service.send_notification(message)