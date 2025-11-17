"""
Review-related Celery Tasks.

This module contains background tasks for review management:
- Sending automated review requests after completed appointments
- Reminding users to leave reviews
- Aggregating review statistics
- Managing review helpfulness scores

Author: Bookora Team
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from celery import shared_task
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
import logging

from app.core.database import SessionLocal
from app.models.appointments import Appointment, AppointmentStatus
from app.models.reviews import Review
from app.models.clients import Client
from app.models.businesses import Business
from app.models.notifications import NotificationLog, NotificationType, NotificationEvent, NotificationStatus
from app.services.fcm_service import fcm_service, FCMMessage

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


@shared_task(bind=True, max_retries=3)
def process_completed_appointments(self):
    """
    Process completed appointments and send review requests.
    
    This task runs daily and:
    - Identifies appointments completed in the last 24 hours
    - Checks if client has already reviewed the business
    - Sends review request notification if no review exists
    
    Returns:
        dict: Summary of review requests sent
    """
    db = get_db()
    try:
        logger.info("Processing completed appointments for review requests...")
        
        # Get appointments completed in the last 24-48 hours (1 day buffer)
        yesterday = datetime.utcnow() - timedelta(days=1)
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        
        completed_appointments = db.query(Appointment).filter(
            and_(
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.appointment_date >= two_days_ago,
                Appointment.appointment_date <= yesterday
            )
        ).all()
        
        logger.info(f"Found {len(completed_appointments)} completed appointments")
        
        results = {"requests_sent": 0, "skipped": 0, "errors": 0}
        
        for appointment in completed_appointments:
            try:
                # Check if client has already reviewed this business
                existing_review = db.query(Review).filter(
                    and_(
                        Review.client_id == appointment.client_id,
                        Review.business_id == appointment.business_id,
                        Review.appointment_id == appointment.id
                    )
                ).first()
                
                if existing_review:
                    results["skipped"] += 1
                    continue
                
                # Check if we've already sent a review request for this appointment
                existing_notification = db.query(NotificationLog).filter(
                    and_(
                        NotificationLog.related_appointment_id == appointment.id,
                        NotificationLog.event == NotificationEvent.BUSINESS_REVIEW_REQUEST
                    )
                ).first()
                
                if existing_notification:
                    results["skipped"] += 1
                    continue
                
                # Send review request
                success = send_review_request_notification(
                    db=db,
                    appointment=appointment
                )
                
                if success:
                    results["requests_sent"] += 1
                else:
                    results["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing appointment {appointment.id}: {e}")
                results["errors"] += 1
        
        db.commit()
        logger.info(f"Review request processing complete: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in process_completed_appointments: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


def send_review_request_notification(
    db: Session,
    appointment: Appointment
) -> bool:
    """
    Send a review request notification to a client.
    
    Args:
        db: Database session
        appointment: Completed appointment object
    
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        # Get client and business information
        client = db.query(Client).filter(Client.id == appointment.client_id).first()
        business = db.query(Business).filter(Business.id == appointment.business_id).first()
        
        if not client or not business:
            logger.error(f"Client or business not found for appointment {appointment.id}")
            return False
        
        # Format appointment date
        appointment_date_str = appointment.appointment_date.strftime("%B %d, %Y")
        
        # Create notification subject and body
        subject = f"How was your experience at {business.name}?"
        body = f"""
Hi {client.first_name},

Thank you for visiting {business.name} on {appointment_date_str}!

We hope you had a great experience. Would you mind taking a moment to share your feedback? 
Your review helps other customers and supports local businesses.

Tap here to leave a review.

Thank you for using Bookora!
"""
        
        # Send push notification if FCM token exists
        notification_sent = False
        if client.fcm_token:
            try:
                message = FCMMessage(
                    token=client.fcm_token,
                    title=subject,
                    body=f"Share your experience at {business.name}",
                    data={
                        "type": "review_request",
                        "appointment_id": str(appointment.id),
                        "business_id": str(business.id),
                        "business_name": business.name
                    },
                    click_action="REVIEW_SCREEN"
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
        
        # Log notification (regardless of push notification success)
        notification_log = NotificationLog(
            recipient_firebase_uid=client.firebase_uid,
            recipient_email=client.email if hasattr(client, 'email') else None,
            notification_type=NotificationType.PUSH,
            event=NotificationEvent.BUSINESS_REVIEW_REQUEST,
            subject=subject,
            body=body,
            status=NotificationStatus.SENT if notification_sent else NotificationStatus.FAILED,
            sent_at=datetime.utcnow() if notification_sent else None,
            failed_at=None if notification_sent else datetime.utcnow(),
            related_appointment_id=appointment.id,
            related_client_id=client.id,
            related_business_id=business.id
        )
        
        db.add(notification_log)
        db.commit()
        
        return notification_sent
        
    except Exception as e:
        logger.error(f"Error sending review request notification: {e}")
        return False


@shared_task(bind=True)
def aggregate_business_review_stats(self, business_id: str):
    """
    Aggregate and update review statistics for a business.
    
    This task calculates:
    - Average rating
    - Total review count
    - Rating distribution (1-5 stars)
    
    Args:
        business_id: UUID of the business
    
    Returns:
        dict: Aggregated review statistics
    """
    db = get_db()
    try:
        from uuid import UUID
        
        business = db.query(Business).filter(
            Business.id == UUID(business_id)
        ).first()
        
        if not business:
            logger.error(f"Business {business_id} not found")
            return {"error": "Business not found"}
        
        # Get all reviews for this business
        reviews = db.query(Review).filter(
            and_(
                Review.business_id == business.id,
                Review.is_active == True
            )
        ).all()
        
        if not reviews:
            return {
                "business_id": business_id,
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        # Calculate statistics
        total_reviews = len(reviews)
        total_rating = sum(review.rating for review in reviews)
        average_rating = total_rating / total_reviews
        
        # Rating distribution
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in reviews:
            rating_distribution[review.rating] = rating_distribution.get(review.rating, 0) + 1
        
        # Update business average rating (if field exists)
        if hasattr(business, 'average_rating'):
            business.average_rating = average_rating
        if hasattr(business, 'total_reviews'):
            business.total_reviews = total_reviews
        
        db.commit()
        
        result = {
            "business_id": business_id,
            "average_rating": round(average_rating, 2),
            "total_reviews": total_reviews,
            "rating_distribution": rating_distribution
        }
        
        logger.info(f"Review stats aggregated for business {business_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error aggregating review stats: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(bind=True)
def send_review_reminder(self, appointment_id: str):
    """
    Send a reminder to leave a review if client hasn't reviewed yet.
    
    This can be called 7 days after an appointment if no review exists.
    
    Args:
        appointment_id: UUID of the appointment
    
    Returns:
        dict: Reminder send result
    """
    db = get_db()
    try:
        from uuid import UUID
        
        appointment = db.query(Appointment).filter(
            Appointment.id == UUID(appointment_id)
        ).first()
        
        if not appointment:
            return {"success": False, "error": "Appointment not found"}
        
        # Check if review exists
        existing_review = db.query(Review).filter(
            and_(
                Review.appointment_id == appointment.id,
                Review.is_active == True
            )
        ).first()
        
        if existing_review:
            return {"success": False, "message": "Review already exists"}
        
        # Send reminder notification
        success = send_review_request_notification(db, appointment)
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error sending review reminder: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task
def update_review_helpfulness_scores():
    """
    Update helpfulness scores for reviews based on user votes.
    
    This task can be used to calculate trending or featured reviews.
    Currently a placeholder for future implementation.
    """
    logger.info("Update review helpfulness scores task executed")
    return {"status": "placeholder"}

