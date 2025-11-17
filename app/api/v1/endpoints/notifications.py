"""
Notification API endpoints for the Bookora application.

This module handles notification logs, preferences, and FCM token management.

Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.notifications import (
    NotificationLog, NotificationPreference,
    NotificationType, NotificationEvent, NotificationStatus
)
from app.models.clients import Client
from app.models.businesses import Business
from app.schemas.notifications import (
    NotificationResponse, 
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate
)

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    status: Optional[NotificationStatus] = Query(None, description="Filter by status"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get notification history for current user.
    
    Returns paginated list of notifications sent to the user.
    """
    # Verify user exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Build query
    query = db.query(NotificationLog).filter(
        NotificationLog.recipient_firebase_uid == firebase_uid
    )
    
    # Apply filters
    if status:
        query = query.filter(NotificationLog.status == status)
    
    if notification_type:
        query = query.filter(NotificationLog.notification_type == notification_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    notifications = (
        query.order_by(desc(NotificationLog.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return NotificationListResponse(
        notifications=notifications,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def get_notification_preferences(
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get notification preferences for current user.
    
    Returns all notification preference settings for the user.
    """
    # Verify user exists and get their ID
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Get preferences
    if client:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.client_id == client.id
        ).all()
    else:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.business_id == business.id
        ).all()
    
    return preferences


@router.put("/preferences/{event}")
async def update_notification_preference(
    event: NotificationEvent,
    preference_update: NotificationPreferenceUpdate,
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update notification preference for a specific event.
    
    Allows users to enable/disable notifications for specific events.
    """
    # Verify user exists and get their ID
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Find or create preference
    if client:
        preference = db.query(NotificationPreference).filter(
            NotificationPreference.client_id == client.id,
            NotificationPreference.event == event,
            NotificationPreference.notification_type == preference_update.notification_type
        ).first()
        
        if not preference:
            preference = NotificationPreference(
                client_id=client.id,
                event=event,
                notification_type=preference_update.notification_type,
                is_enabled=preference_update.is_enabled
            )
            db.add(preference)
        else:
            preference.is_enabled = preference_update.is_enabled
    else:
        preference = db.query(NotificationPreference).filter(
            NotificationPreference.business_id == business.id,
            NotificationPreference.event == event,
            NotificationPreference.notification_type == preference_update.notification_type
        ).first()
        
        if not preference:
            preference = NotificationPreference(
                business_id=business.id,
                event=event,
                notification_type=preference_update.notification_type,
                is_enabled=preference_update.is_enabled
            )
            db.add(preference)
        else:
            preference.is_enabled = preference_update.is_enabled
    
    db.commit()
    db.refresh(preference)
    
    return {"status": "success", "message": "Notification preference updated"}


@router.put("/fcm-token")
async def update_fcm_token(
    fcm_token: str,
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update FCM token for push notifications.
    
    Updates the user's Firebase Cloud Messaging token for receiving push notifications.
    """
    # Find user
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Update FCM token
    if client:
        client.fcm_token = fcm_token
        client.updated_at = datetime.utcnow()
    else:
        business.fcm_token = fcm_token
        business.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "success", "message": "FCM token updated successfully"}


@router.delete("/fcm-token")
async def remove_fcm_token(
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Remove FCM token (for logout/unregister device).
    
    Clears the user's FCM token to stop receiving push notifications on this device.
    """
    # Find user
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Clear FCM token
    if client:
        client.fcm_token = None
        client.updated_at = datetime.utcnow()
    else:
        business.fcm_token = None
        business.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "success", "message": "FCM token removed successfully"}


@router.get("/unread-count")
async def get_unread_notification_count(
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Get count of unread notifications.
    
    Returns the number of unread notifications for quick badge display.
    """
    # Verify user exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    
    if not client and not business:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Count unread notifications (sent but not delivered)
    unread_count = db.query(NotificationLog).filter(
        NotificationLog.recipient_firebase_uid == firebase_uid,
        NotificationLog.status == NotificationStatus.SENT
    ).count()
    
    return {"unread_count": unread_count}


@router.put("/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Mark a specific notification as read.
    
    Updates the notification status to indicate it has been seen by the user.
    """
    notification = db.query(NotificationLog).filter(
        NotificationLog.id == notification_id,
        NotificationLog.recipient_firebase_uid == firebase_uid
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Mark as delivered (read)
    notification.mark_delivered()
    
    db.commit()
    
    return {"status": "success", "message": "Notification marked as read"}


@router.put("/mark-all-read")
async def mark_all_notifications_read(
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications as read.
    
    Bulk update to mark all unread notifications as read.
    """
    # Update all unread notifications
    db.query(NotificationLog).filter(
        NotificationLog.recipient_firebase_uid == firebase_uid,
        NotificationLog.status == NotificationStatus.SENT
    ).update({"status": NotificationStatus.DELIVERED})
    
    db.commit()
    
    return {"status": "success", "message": "All notifications marked as read"}
