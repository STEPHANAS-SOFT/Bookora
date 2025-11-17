"""
Celery Configuration for Bookora Backend.

This module configures Celery for handling background tasks like:
- Appointment reminders (24h and 2h before appointments)
- Notification sending (email, push notifications)
- Review request automation
- Database cleanup and maintenance
- Business statistics aggregation

Author: Bookora Team
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
import logging

# Configure logging for Celery
logger = logging.getLogger(__name__)

# Initialize Celery app
# Using Redis as both message broker and result backend
celery_app = Celery(
    "bookora",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.appointment_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.review_tasks"
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # Soft limit at 25 minutes
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task routing - can be extended for different queues
    task_routes={
        "app.tasks.appointment_tasks.*": {"queue": "appointments"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "app.tasks.review_tasks.*": {"queue": "reviews"},
    },
    
    # Task priority settings
    task_default_priority=5,
    task_inherit_parent_priority=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Check for appointment reminders every 5 minutes
        "check-appointment-reminders": {
            "task": "app.tasks.appointment_tasks.check_and_send_reminders",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
            "options": {"queue": "appointments"},
        },
        
        # Process completed appointments and send review requests daily
        "process-completed-appointments": {
            "task": "app.tasks.review_tasks.process_completed_appointments",
            "schedule": crontab(hour=10, minute=0),  # Daily at 10:00 AM
            "options": {"queue": "reviews"},
        },
        
        # Clean up old notification logs weekly
        "cleanup-old-notifications": {
            "task": "app.tasks.maintenance_tasks.cleanup_old_notifications",
            "schedule": crontab(day_of_week=1, hour=2, minute=0),  # Monday at 2:00 AM
            "options": {"queue": "maintenance"},
        },
        
        # Clean up expired appointments daily
        "cleanup-expired-appointments": {
            "task": "app.tasks.maintenance_tasks.cleanup_expired_appointments",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM
            "options": {"queue": "maintenance"},
        },
        
        # Retry failed notifications every hour
        "retry-failed-notifications": {
            "task": "app.tasks.notification_tasks.retry_failed_notifications",
            "schedule": crontab(minute=0),  # Every hour
            "options": {"queue": "notifications"},
        },
        
        # Generate daily business statistics
        "generate-daily-statistics": {
            "task": "app.tasks.maintenance_tasks.generate_daily_statistics",
            "schedule": crontab(hour=1, minute=0),  # Daily at 1:00 AM
            "options": {"queue": "maintenance"},
        },
        
        # Clean up stale chat rooms monthly
        "cleanup-stale-chatrooms": {
            "task": "app.tasks.maintenance_tasks.cleanup_stale_chatrooms",
            "schedule": crontab(day_of_month=1, hour=4, minute=0),  # 1st of month at 4:00 AM
            "options": {"queue": "maintenance"},
        },
    },
)


# Task error handler
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    logger.info(f"Request: {self.request!r}")
    return f"Celery is working! Task ID: {self.request.id}"


# Export celery app
__all__ = ["celery_app"]

