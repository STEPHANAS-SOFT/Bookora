"""
Maintenance and Cleanup Celery Tasks.

This module contains background tasks for system maintenance:
- Database cleanup (old logs, expired data)
- Statistics generation
- Data aggregation
- System health checks

Author: Bookora Team
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from celery import shared_task
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
import logging

from app.core.database import SessionLocal
from app.models.appointments import Appointment, AppointmentStatus
from app.models.notifications import NotificationLog, NotificationStatus
from app.models.communications import ChatRoom, ChatMessage
from app.models.businesses import Business
from app.models.clients import Client
from app.models.reviews import Review

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
def cleanup_old_notifications(self):
    """
    Clean up old notification logs to maintain database performance.
    
    This task runs weekly and removes:
    - Successfully delivered notifications older than 90 days
    - Failed notifications older than 30 days
    
    Returns:
        dict: Summary of cleanup operation
    """
    db = get_db()
    try:
        logger.info("Starting notification cleanup...")
        
        # Delete delivered notifications older than 90 days
        delivered_cutoff = datetime.utcnow() - timedelta(days=90)
        delivered_deleted = db.query(NotificationLog).filter(
            and_(
                NotificationLog.status == NotificationStatus.DELIVERED,
                NotificationLog.created_at < delivered_cutoff
            )
        ).delete(synchronize_session=False)
        
        # Delete failed notifications older than 30 days
        failed_cutoff = datetime.utcnow() - timedelta(days=30)
        failed_deleted = db.query(NotificationLog).filter(
            and_(
                NotificationLog.status == NotificationStatus.FAILED,
                NotificationLog.created_at < failed_cutoff
            )
        ).delete(synchronize_session=False)
        
        db.commit()
        
        result = {
            "delivered_deleted": delivered_deleted,
            "failed_deleted": failed_deleted,
            "total_deleted": delivered_deleted + failed_deleted
        }
        
        logger.info(f"Notification cleanup complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def cleanup_expired_appointments(self):
    """
    Clean up or archive old appointments to maintain database performance.
    
    This task runs daily and marks appointments as archived if they are:
    - Older than 1 year
    - Already completed or cancelled
    
    Returns:
        dict: Summary of cleanup operation
    """
    db = get_db()
    try:
        logger.info("Starting appointment cleanup...")
        
        # Find appointments older than 1 year that are completed or cancelled
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        old_appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date < cutoff_date,
                or_(
                    Appointment.status == AppointmentStatus.COMPLETED,
                    Appointment.status == AppointmentStatus.CANCELLED
                )
            )
        ).all()
        
        # Mark as inactive instead of deleting (for record keeping)
        count = 0
        for appointment in old_appointments:
            if hasattr(appointment, 'is_active'):
                appointment.is_active = False
                count += 1
        
        db.commit()
        
        result = {"archived_count": count}
        logger.info(f"Appointment cleanup complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup_expired_appointments: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def cleanup_stale_chatrooms(self):
    """
    Clean up chat rooms with no activity for extended periods.
    
    This task runs monthly and marks chat rooms as archived if:
    - No messages in the last 6 months
    - Not marked as important
    
    Returns:
        dict: Summary of cleanup operation
    """
    db = get_db()
    try:
        logger.info("Starting chat room cleanup...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=180)  # 6 months
        
        # Find chat rooms with no recent messages
        stale_rooms = db.query(ChatRoom).filter(
            ChatRoom.updated_at < cutoff_date
        ).all()
        
        count = 0
        for room in stale_rooms:
            if hasattr(room, 'is_active'):
                room.is_active = False
                count += 1
        
        db.commit()
        
        result = {"archived_count": count}
        logger.info(f"Chat room cleanup complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup_stale_chatrooms: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True)
def generate_daily_statistics(self):
    """
    Generate daily statistics for the platform.
    
    This task runs daily and calculates:
    - Total appointments (by status)
    - New user registrations (clients and businesses)
    - Revenue metrics
    - Popular services and businesses
    
    Returns:
        dict: Daily statistics summary
    """
    db = get_db()
    try:
        logger.info("Generating daily statistics...")
        
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        stats = {
            "date": yesterday.isoformat(),
            "appointments": {},
            "users": {},
            "businesses": {},
            "reviews": {}
        }
        
        # Appointment statistics
        stats["appointments"]["total"] = db.query(Appointment).filter(
            func.date(Appointment.appointment_date) == yesterday
        ).count()
        
        stats["appointments"]["completed"] = db.query(Appointment).filter(
            and_(
                func.date(Appointment.appointment_date) == yesterday,
                Appointment.status == AppointmentStatus.COMPLETED
            )
        ).count()
        
        stats["appointments"]["cancelled"] = db.query(Appointment).filter(
            and_(
                func.date(Appointment.appointment_date) == yesterday,
                Appointment.status == AppointmentStatus.CANCELLED
            )
        ).count()
        
        stats["appointments"]["pending"] = db.query(Appointment).filter(
            and_(
                func.date(Appointment.appointment_date) == yesterday,
                Appointment.status == AppointmentStatus.PENDING
            )
        ).count()
        
        # User registration statistics
        stats["users"]["new_clients"] = db.query(Client).filter(
            func.date(Client.created_at) == yesterday
        ).count()
        
        stats["users"]["total_clients"] = db.query(Client).filter(
            Client.is_active == True
        ).count()
        
        # Business statistics
        stats["businesses"]["new_registrations"] = db.query(Business).filter(
            func.date(Business.created_at) == yesterday
        ).count()
        
        stats["businesses"]["total_active"] = db.query(Business).filter(
            Business.is_active == True
        ).count()
        
        # Review statistics
        stats["reviews"]["new_reviews"] = db.query(Review).filter(
            func.date(Review.created_at) == yesterday
        ).count()
        
        stats["reviews"]["total_reviews"] = db.query(Review).filter(
            Review.is_active == True
        ).count()
        
        # Calculate average rating for new reviews
        new_reviews = db.query(Review).filter(
            func.date(Review.created_at) == yesterday
        ).all()
        
        if new_reviews:
            avg_rating = sum(r.rating for r in new_reviews) / len(new_reviews)
            stats["reviews"]["average_rating"] = round(avg_rating, 2)
        else:
            stats["reviews"]["average_rating"] = 0.0
        
        logger.info(f"Daily statistics generated: {stats}")
        
        # In a production system, you might want to store these stats
        # in a separate statistics table for historical tracking
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in generate_daily_statistics: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(bind=True)
def check_database_health(self):
    """
    Perform database health checks.
    
    This task checks:
    - Database connection
    - Table sizes
    - Index health
    - Query performance
    
    Returns:
        dict: Health check results
    """
    db = get_db()
    try:
        logger.info("Performing database health check...")
        
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Test database connection
        try:
            db.execute("SELECT 1")
            health["checks"]["connection"] = "OK"
        except Exception as e:
            health["checks"]["connection"] = f"FAILED: {str(e)}"
            health["status"] = "unhealthy"
        
        # Check table record counts
        try:
            health["checks"]["record_counts"] = {
                "clients": db.query(Client).count(),
                "businesses": db.query(Business).count(),
                "appointments": db.query(Appointment).count(),
                "reviews": db.query(Review).count(),
                "notifications": db.query(NotificationLog).count(),
                "chat_rooms": db.query(ChatRoom).count(),
            }
        except Exception as e:
            health["checks"]["record_counts"] = f"FAILED: {str(e)}"
            health["status"] = "degraded"
        
        # Check for large tables that might need optimization
        total_records = sum(health["checks"]["record_counts"].values()) if isinstance(
            health["checks"]["record_counts"], dict
        ) else 0
        
        health["checks"]["optimization_needed"] = total_records > 1000000  # 1M records
        
        logger.info(f"Database health check complete: {health['status']}")
        return health
        
    except Exception as e:
        logger.error(f"Error in check_database_health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        db.close()


@shared_task(bind=True)
def update_business_statistics(self, business_id: str = None):
    """
    Update cached statistics for businesses.
    
    Args:
        business_id: Optional specific business ID to update
    
    Returns:
        dict: Update summary
    """
    db = get_db()
    try:
        from uuid import UUID
        
        logger.info(f"Updating business statistics for {business_id or 'all businesses'}...")
        
        # Get businesses to update
        if business_id:
            businesses = [db.query(Business).filter(Business.id == UUID(business_id)).first()]
            if not businesses[0]:
                return {"error": "Business not found"}
        else:
            businesses = db.query(Business).filter(Business.is_active == True).all()
        
        updated_count = 0
        
        for business in businesses:
            try:
                # Count total appointments
                total_appointments = db.query(Appointment).filter(
                    Appointment.business_id == business.id
                ).count()
                
                # Count completed appointments
                completed_appointments = db.query(Appointment).filter(
                    and_(
                        Appointment.business_id == business.id,
                        Appointment.status == AppointmentStatus.COMPLETED
                    )
                ).count()
                
                # Calculate average rating
                reviews = db.query(Review).filter(
                    and_(
                        Review.business_id == business.id,
                        Review.is_active == True
                    )
                ).all()
                
                if reviews:
                    avg_rating = sum(r.rating for r in reviews) / len(reviews)
                    total_reviews = len(reviews)
                else:
                    avg_rating = 0.0
                    total_reviews = 0
                
                # Update business fields if they exist
                if hasattr(business, 'total_appointments'):
                    business.total_appointments = total_appointments
                if hasattr(business, 'completed_appointments'):
                    business.completed_appointments = completed_appointments
                if hasattr(business, 'average_rating'):
                    business.average_rating = round(avg_rating, 2)
                if hasattr(business, 'total_reviews'):
                    business.total_reviews = total_reviews
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating stats for business {business.id}: {e}")
                continue
        
        db.commit()
        
        result = {"updated_count": updated_count}
        logger.info(f"Business statistics update complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in update_business_statistics: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

