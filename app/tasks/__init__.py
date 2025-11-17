"""
Background Tasks Package for Bookora.

This package contains Celery tasks for automated operations:
- Appointment tasks: Reminders, confirmations, status updates
- Notification tasks: Email, push notifications, SMS
- Maintenance tasks: Database cleanup, statistics generation
- Review tasks: Automated review requests after appointments

Author: Bookora Team
"""

__all__ = [
    "appointment_tasks",
    "notification_tasks",
    "maintenance_tasks",
    "review_tasks"
]

