"""
Notification-related Celery Tasks.

This module contains background tasks for notification management:
- Retrying failed notifications
- Sending bulk notifications
- Processing notification queues
- Managing notification delivery status

Author: Bookora Team
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from celery import shared_task
from sqlalchemy import and_
from sqlalchemy.orm import Session
import logging

from app.core.database import SessionLocal
from app.models.notifications import NotificationLog, NotificationStatus, NotificationType, NotificationEvent
from app.models.clients import Client
from app.models.businesses import Business
from app.services.fcm_service import fcm_service, FCMMessage
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session for background tasks."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def retry_failed_notifications(self):
    """
    Retry sending failed notifications.
    
    This task runs hourly and attempts to resend notifications that:
    - Have status FAILED
    - Haven't exceeded max retry count
    - Are less than 24 hours old
    
    Returns:
        dict: Summary of retry attempts
    """
    db = get_db()
    try:
        logger.info("Starting failed notification retry process...")
        
        # Get failed notifications that can be retried
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        failed_notifications = db.query(NotificationLog).filter(
            and_(
                NotificationLog.status == NotificationStatus.FAILED,
                NotificationLog.retry_count < NotificationLog.max_retries,
                NotificationLog.created_at >= cutoff_time
            )
        ).limit(100).all()  # Process in batches of 100
        
        logger.info(f"Found {len(failed_notifications)} notifications to retry")
        
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        for notification in failed_notifications:
            try:
                success = False
                
                # Try to resend based on notification type
                if notification.notification_type == NotificationType.PUSH:
                    success = await_retry_push_notification(db, notification)
                elif notification.notification_type == NotificationType.EMAIL:
                    # Email retry logic would go here
                    # For now, we'll skip email retries
                    results["skipped"] += 1
                    continue
                else:
                    results["skipped"] += 1
                    continue
                
                # Update notification status
                notification.retry_count += 1
                
                if success:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.utcnow()
                    results["success"] += 1
                else:
                    notification.failed_at = datetime.utcnow()
                    results["failed"] += 1
                
            except Exception as e:
                logger.error(f"Error retrying notification {notification.id}: {e}")
                notification.retry_count += 1
                notification.error_message = str(e)
                results["failed"] += 1
        
        db.commit()
        logger.info(f"Retry process complete: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in retry_failed_notifications: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


def await_retry_push_notification(db: Session, notification: NotificationLog) -> bool:
    """
    Retry sending a push notification.
    
    Args:
        db: Database session
        notification: NotificationLog object to retry
    
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        # Get recipient information
        client = None
        business = None
        fcm_token = None
        
        if notification.related_client_id:
            client = db.query(Client).filter(
                Client.id == notification.related_client_id
            ).first()
            if client and hasattr(client, 'fcm_token'):
                fcm_token = client.fcm_token
        
        if notification.related_business_id and not fcm_token:
            business = db.query(Business).filter(
                Business.id == notification.related_business_id
            ).first()
            if business and hasattr(business, 'fcm_token'):
                fcm_token = business.fcm_token
        
        if not fcm_token:
            logger.error(f"No FCM token found for notification {notification.id}")
            return False
        
        # Create FCM message
        message = FCMMessage(
            token=fcm_token,
            title=notification.subject or "Notification from Bookora",
            body=notification.body,
            data={
                "notification_id": str(notification.id),
                "event": notification.event.value if notification.event else "general",
                "type": "retry"
            }
        )
        
        # Send notification using FCM service
        # Note: This is a synchronous call in an async context
        # In production, you might want to use asyncio properly
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fcm_service.send_notification(message))
        loop.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in await_retry_push_notification: {e}")
        return False


@shared_task(bind=True)
def send_bulk_notification(
    self,
    recipient_ids: List[str],
    notification_type: str,
    event: str,
    subject: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
):
    """
    Send notifications to multiple recipients.
    
    Args:
        recipient_ids: List of Firebase UIDs
        notification_type: Type of notification (push, email, sms)
        event: Notification event
        subject: Notification subject
        body: Notification body
        data: Additional data to include
    
    Returns:
        dict: Summary of bulk send operation
    """
    db = get_db()
    try:
        logger.info(f"Starting bulk notification send to {len(recipient_ids)} recipients")
        
        results = {"success": 0, "failed": 0, "total": len(recipient_ids)}
        
        for firebase_uid in recipient_ids:
            try:
                # Create notification task for each recipient
                send_single_notification.delay(
                    firebase_uid=firebase_uid,
                    notification_type=notification_type,
                    event=event,
                    subject=subject,
                    body=body,
                    data=data
                )
                results["success"] += 1
                
            except Exception as e:
                logger.error(f"Error queuing notification for {firebase_uid}: {e}")
                results["failed"] += 1
        
        logger.info(f"Bulk notification queuing complete: {results}")
        return results
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def send_single_notification(
    self,
    firebase_uid: str,
    notification_type: str,
    event: str,
    subject: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
):
    """
    Send a single notification to a user.
    
    Args:
        firebase_uid: Recipient's Firebase UID
        notification_type: Type of notification (push, email, sms)
        event: Notification event
        subject: Notification subject
        body: Notification body
        data: Additional data to include
    
    Returns:
        dict: Notification send result
    """
    db = get_db()
    try:
        # Find recipient (try client first, then business)
        client = db.query(Client).filter(
            Client.firebase_uid == firebase_uid
        ).first()
        
        business = None
        if not client:
            business = db.query(Business).filter(
                Business.firebase_uid == firebase_uid
            ).first()
        
        if not client and not business:
            logger.error(f"Recipient not found: {firebase_uid}")
            return {"success": False, "error": "Recipient not found"}
        
        # Get FCM token
        fcm_token = None
        if client and hasattr(client, 'fcm_token'):
            fcm_token = client.fcm_token
        elif business and hasattr(business, 'fcm_token'):
            fcm_token = business.fcm_token
        
        notification_sent = False
        
        # Send push notification if token exists
        if notification_type == "push" and fcm_token:
            try:
                message = FCMMessage(
                    token=fcm_token,
                    title=subject,
                    body=body,
                    data=data or {}
                )
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                notification_sent = loop.run_until_complete(
                    fcm_service.send_notification(message)
                )
                loop.close()
                
            except Exception as e:
                logger.error(f"FCM notification failed: {e}")
        
        # Create notification log
        notification_log = NotificationLog(
            recipient_firebase_uid=firebase_uid,
            recipient_email=getattr(client or business, 'email', None),
            notification_type=NotificationType(notification_type),
            event=NotificationEvent(event),
            subject=subject,
            body=body,
            status=NotificationStatus.SENT if notification_sent else NotificationStatus.FAILED,
            sent_at=datetime.utcnow() if notification_sent else None,
            failed_at=None if notification_sent else datetime.utcnow(),
            related_client_id=client.id if client else None,
            related_business_id=business.id if business else None,
            extra_data=data
        )
        
        db.add(notification_log)
        db.commit()
        
        return {
            "success": notification_sent,
            "notification_id": str(notification_log.id)
        }
        
    except Exception as e:
        logger.error(f"Error sending single notification: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task
def cleanup_notification_delivery_status():
    """
    Update delivery status for notifications based on external service callbacks.
    
    This task would integrate with FCM delivery reports, email delivery reports, etc.
    For now, it's a placeholder for future implementation.
    """
    logger.info("Cleanup notification delivery status task executed")
    return {"status": "placeholder"}

