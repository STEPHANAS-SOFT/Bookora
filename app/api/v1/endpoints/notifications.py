"""
Notification API endpoints for the Bookora application.

This module handles notification management, preferences, and delivery status.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.notifications import (
    NotificationLog, NotificationTemplate, NotificationPreference,
    NotificationType, NotificationEvent, NotificationStatus
)
from app.models.clients import Client
from app.models.businesses import Business
from app.core.auth import get_current_firebase_user

router = APIRouter()


@router.get("/my-notifications", response_model=List[dict])
async def get_my_notifications(
    notification_type: Optional[NotificationType] = Query(None),
    status: Optional[NotificationStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get notification history for current user."""
    # Get user ID (client or business)
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client:
        query = db.query(NotificationLog).filter(NotificationLog.client_id == client.id)
    elif business:
        query = db.query(NotificationLog).filter(NotificationLog.business_id == business.id)
    else:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Apply filters
    if notification_type:
        query = query.filter(NotificationLog.notification_type == notification_type)
    if status:
        query = query.filter(NotificationLog.status == status)
    
    # Get notifications
    notifications = (
        query.order_by(NotificationLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Format response
    result = []
    for notification in notifications:
        result.append({
            "id": str(notification.id),
            "notification_type": notification.notification_type,
            "event": notification.event,
            "title": notification.title,
            "message": notification.message,
            "status": notification.status,
            "sent_at": notification.sent_at,
            "delivered_at": notification.delivered_at,
            "error_message": notification.error_message,
            "created_at": notification.created_at
        })
    
    return result


@router.get("/preferences", response_model=dict)
async def get_notification_preferences(
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Get notification preferences for current user."""
    # Get user ID (client or business)
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.client_id == client.id
        ).all()
        user_id = client.id
        user_type = "client"
    elif business:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.business_id == business.id
        ).all()
        user_id = business.id
        user_type = "business"
    else:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Convert to dictionary format
    prefs_dict = {}
    for pref in preferences:
        event_key = f"{pref.event}_{pref.notification_type}"
        prefs_dict[event_key] = pref.is_enabled
    
    return {
        "user_id": str(user_id),
        "user_type": user_type,
        "preferences": prefs_dict
    }


@router.put("/preferences", response_model=dict)
async def update_notification_preferences(
    preferences: dict,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences for current user."""
    # Get user ID (client or business)
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client:
        user_id = client.id
        user_type = "client"
    elif business:
        user_id = business.id
        user_type = "business"
    else:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Update preferences
    updated_count = 0
    for pref_key, is_enabled in preferences.items():
        try:
            # Parse event and notification type from key (e.g., "appointment_booked_email")
            parts = pref_key.rsplit('_', 1)
            if len(parts) != 2:
                continue
                
            event_str, notif_type_str = parts
            
            # Validate enums
            try:
                event = NotificationEvent(event_str)
                notif_type = NotificationType(notif_type_str)
            except ValueError:
                continue
            
            # Find or create preference
            if client:
                pref = (
                    db.query(NotificationPreference)
                    .filter(
                        NotificationPreference.client_id == user_id,
                        NotificationPreference.event == event,
                        NotificationPreference.notification_type == notif_type
                    )
                    .first()
                )
            else:
                pref = (
                    db.query(NotificationPreference)
                    .filter(
                        NotificationPreference.business_id == user_id,
                        NotificationPreference.event == event,
                        NotificationPreference.notification_type == notif_type
                    )
                    .first()
                )
            
            if pref:
                pref.is_enabled = bool(is_enabled)
                updated_count += 1
            else:
                # Create new preference
                new_pref = NotificationPreference(
                    client_id=user_id if client else None,
                    business_id=user_id if business else None,
                    event=event,
                    notification_type=notif_type,
                    is_enabled=bool(is_enabled)
                )
                db.add(new_pref)
                updated_count += 1
                
        except Exception as e:
            continue
    
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Updated {updated_count} notification preferences"
    }


@router.post("/fcm-token", response_model=dict)
async def update_fcm_token(
    token_data: dict,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Update FCM token for push notifications."""
    fcm_token = token_data.get("fcm_token")
    if not fcm_token:
        raise HTTPException(status_code=400, detail="FCM token is required")
    
    # Update user's FCM token
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if client:
        client.fcm_token = fcm_token
        client.fcm_token_updated_at = datetime.now()
        db.commit()
        return {"status": "success", "message": "Client FCM token updated"}
    elif business:
        business.fcm_token = fcm_token
        business.fcm_token_updated_at = datetime.now()
        db.commit()
        return {"status": "success", "message": "Business FCM token updated"}
    else:
        raise HTTPException(status_code=404, detail="User profile not found")


@router.post("/test-notification", response_model=dict)
async def send_test_notification(
    notification_data: dict,
    current_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db)
):
    """Send a test notification (development only)."""
    from app.core.credentials import is_development
    
    if not is_development():
        raise HTTPException(status_code=403, detail="Test notifications only available in development")
    
    notification_type = notification_data.get("type", "email")
    message = notification_data.get("message", "Test notification")
    
    # Get user
    client = db.query(Client).filter(Client.firebase_uid == current_user["uid"]).first()
    business = db.query(Business).filter(Business.firebase_uid == current_user["uid"]).first()
    
    if not (client or business):
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Create test notification log
    log = NotificationLog(
        client_id=client.id if client else None,
        business_id=business.id if business else None,
        notification_type=NotificationType(notification_type),
        event=NotificationEvent.NEW_MESSAGE,
        title="Test Notification",
        message=message,
        status=NotificationStatus.SENT,
        sent_at=datetime.now()
    )
    
    db.add(log)
    db.commit()
    
    return {"status": "success", "message": "Test notification created"}


@router.get("/templates", response_model=List[dict])
async def get_notification_templates(
    event: Optional[NotificationEvent] = Query(None),
    notification_type: Optional[NotificationType] = Query(None),
    language: str = Query("en", max_length=10),
    db: Session = Depends(get_db)
):
    """Get notification templates (admin or development use)."""
    query = db.query(NotificationTemplate).filter(
        NotificationTemplate.language == language
    )
    
    if event:
        query = query.filter(NotificationTemplate.event == event)
    if notification_type:
        query = query.filter(NotificationTemplate.notification_type == notification_type)
    
    templates = query.all()
    
    result = []
    for template in templates:
        result.append({
            "id": str(template.id),
            "name": template.name,
            "event": template.event,
            "notification_type": template.notification_type,
            "subject": template.subject,
            "body_template": template.body_template,
            "language": template.language,
            "is_active": template.is_active
        })
    
    return result