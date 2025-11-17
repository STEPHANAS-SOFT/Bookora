"""
Appointment-related Celery Tasks.

This module contains background tasks for appointment management:
- Sending appointment reminders (24h and 2h before)
- Updating appointment statuses
- Handling missed appointments
- Processing appointment confirmations

Author: Bookora Team
"""

from datetime import datetime, timedelta
from typing import List, Optional
from celery import shared_task
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
import logging

from app.core.database import SessionLocal
from app.models.appointments import Appointment, AppointmentStatus
from app.models.notifications import NotificationLog, NotificationType, NotificationEvent, NotificationStatus
from app.models.clients import Client
from app.models.businesses import Business
from app.services.fcm_service import send_appointment_notification
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)


def get_db() -> Session:
    """
    Get database session for background tasks.
    Creates a new session that must be closed after use.
    """
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def check_and_send_reminders(self):
    """
    Periodic task to check for upcoming appointments and send reminders.
    
    This task runs every 5 minutes and checks for appointments that need:
    - 24-hour reminder (if within 24-25 hours)
    - 2-hour reminder (if within 2-2.5 hours)
    
    Only sends reminders for CONFIRMED appointments that haven't received
    a reminder of that type yet.
    
    Returns:
        dict: Summary of reminders sent
    """
    db = get_db()
    try:
        logger.info("Starting appointment reminder check...")
        
        now = datetime.utcnow()
        reminders_sent = {"24h": 0, "2h": 0, "errors": 0}
        
        # Get appointments that need 24-hour reminders
        # Looking for appointments between 24 and 25 hours from now
        reminder_24h_start = now + timedelta(hours=24)
        reminder_24h_end = now + timedelta(hours=24, minutes=30)
        
        appointments_24h = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date >= reminder_24h_start,
                Appointment.appointment_date <= reminder_24h_end,
                Appointment.status == AppointmentStatus.CONFIRMED,
                Appointment.reminder_24h_sent == False
            )
        ).all()
        
        logger.info(f"Found {len(appointments_24h)} appointments for 24h reminders")
        
        # Send 24-hour reminders
        for appointment in appointments_24h:
            try:
                success = send_reminder_notification(
                    db=db,
                    appointment=appointment,
                    reminder_type="24h"
                )
                if success:
                    appointment.reminder_24h_sent = True
                    reminders_sent["24h"] += 1
                else:
                    reminders_sent["errors"] += 1
            except Exception as e:
                logger.error(f"Error sending 24h reminder for appointment {appointment.id}: {e}")
                reminders_sent["errors"] += 1
        
        # Get appointments that need 2-hour reminders
        # Looking for appointments between 2 and 2.5 hours from now
        reminder_2h_start = now + timedelta(hours=2)
        reminder_2h_end = now + timedelta(hours=2, minutes=30)
        
        appointments_2h = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date >= reminder_2h_start,
                Appointment.appointment_date <= reminder_2h_end,
                Appointment.status == AppointmentStatus.CONFIRMED,
                Appointment.reminder_2h_sent == False
            )
        ).all()
        
        logger.info(f"Found {len(appointments_2h)} appointments for 2h reminders")
        
        # Send 2-hour reminders
        for appointment in appointments_2h:
            try:
                success = send_reminder_notification(
                    db=db,
                    appointment=appointment,
                    reminder_type="2h"
                )
                if success:
                    appointment.reminder_2h_sent = True
                    reminders_sent["2h"] += 1
                else:
                    reminders_sent["errors"] += 1
            except Exception as e:
                logger.error(f"Error sending 2h reminder for appointment {appointment.id}: {e}")
                reminders_sent["errors"] += 1
        
        db.commit()
        logger.info(f"Reminder check complete: {reminders_sent}")
        return reminders_sent
        
    except Exception as e:
        logger.error(f"Error in check_and_send_reminders: {e}")
        db.rollback()
        # Retry the task
        raise self.retry(exc=e)
    finally:
        db.close()


def send_reminder_notification(
    db: Session,
    appointment: Appointment,
    reminder_type: str
) -> bool:
    """
    Send a reminder notification for an appointment.
    
    Args:
        db: Database session
        appointment: Appointment object
        reminder_type: Type of reminder ("24h" or "2h")
    
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
        
        # Determine notification event type
        if reminder_type == "24h":
            event = NotificationEvent.APPOINTMENT_REMINDER_24H
            time_text = "24 hours"
        else:
            event = NotificationEvent.APPOINTMENT_REMINDER_2H
            time_text = "2 hours"
        
        # Format appointment date
        appointment_date_str = appointment.appointment_date.strftime("%B %d, %Y at %I:%M %p")
        
        # Create notification subject and body
        subject = f"Appointment Reminder - {time_text}"
        body = f"""
Hi {client.first_name},

This is a reminder that you have an appointment with {business.name} in {time_text}.

Appointment Details:
- Business: {business.name}
- Date & Time: {appointment_date_str}
- Duration: {appointment.duration_minutes} minutes
- Confirmation Code: {appointment.confirmation_code}

If you need to reschedule or cancel, please contact us as soon as possible.

Thank you for choosing Bookora!
"""
        
        # Send push notification if FCM token exists
        notification_sent = False
        if client.fcm_token:
            try:
                notification_sent = send_appointment_notification(
                    fcm_token=client.fcm_token,
                    business_name=business.name,
                    appointment_date=appointment_date_str,
                    notification_type="reminder"
                )
            except Exception as e:
                logger.error(f"FCM notification failed: {e}")
        
        # Log notification (regardless of push notification success)
        notification_log = NotificationLog(
            recipient_firebase_uid=client.firebase_uid,
            recipient_email=client.email if hasattr(client, 'email') else None,
            notification_type=NotificationType.PUSH,
            event=event,
            subject=subject,
            body=body,
            status=NotificationStatus.SENT if notification_sent else NotificationStatus.FAILED,
            sent_at=datetime.utcnow() if notification_sent else None,
            related_appointment_id=appointment.id,
            related_client_id=client.id,
            related_business_id=business.id
        )
        
        db.add(notification_log)
        db.commit()
        
        return notification_sent
        
    except Exception as e:
        logger.error(f"Error sending reminder notification: {e}")
        return False


@shared_task(bind=True, max_retries=3)
def mark_missed_appointments(self):
    """
    Mark appointments as MISSED if they're past their date and still CONFIRMED.
    
    This task runs periodically to update the status of appointments that
    were not completed or cancelled and are now past their scheduled time.
    
    Returns:
        dict: Number of appointments marked as missed
    """
    db = get_db()
    try:
        logger.info("Checking for missed appointments...")
        
        now = datetime.utcnow()
        # Add buffer of 1 hour after appointment time before marking as missed
        cutoff_time = now - timedelta(hours=1)
        
        missed_appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date < cutoff_time,
                Appointment.status == AppointmentStatus.CONFIRMED
            )
        ).all()
        
        count = 0
        for appointment in missed_appointments:
            appointment.status = AppointmentStatus.CANCELLED
            # Could also add a cancellation reason field
            count += 1
        
        db.commit()
        logger.info(f"Marked {count} appointments as missed")
        return {"missed_count": count}
        
    except Exception as e:
        logger.error(f"Error marking missed appointments: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True)
def send_appointment_confirmation(
    self,
    appointment_id: str,
    firebase_uid: str
):
    """
    Send appointment confirmation notification.
    
    Args:
        appointment_id: UUID of the appointment
        firebase_uid: Firebase UID of the recipient
    
    Returns:
        dict: Confirmation status
    """
    db = get_db()
    try:
        from uuid import UUID
        
        appointment = db.query(Appointment).filter(
            Appointment.id == UUID(appointment_id)
        ).first()
        
        if not appointment:
            logger.error(f"Appointment {appointment_id} not found")
            return {"success": False, "error": "Appointment not found"}
        
        client = db.query(Client).filter(Client.id == appointment.client_id).first()
        business = db.query(Business).filter(Business.id == appointment.business_id).first()
        
        if not client or not business:
            logger.error(f"Client or business not found for appointment {appointment_id}")
            return {"success": False, "error": "Related entities not found"}
        
        # Format appointment date
        appointment_date_str = appointment.appointment_date.strftime("%B %d, %Y at %I:%M %p")
        
        # Send notification
        notification_sent = False
        if client.fcm_token:
            notification_sent = send_appointment_notification(
                fcm_token=client.fcm_token,
                business_name=business.name,
                appointment_date=appointment_date_str,
                notification_type="confirmed"
            )
        
        # Log notification
        subject = "Appointment Confirmed"
        body = f"Your appointment with {business.name} on {appointment_date_str} has been confirmed. Confirmation code: {appointment.confirmation_code}"
        
        notification_log = NotificationLog(
            recipient_firebase_uid=firebase_uid,
            recipient_email=client.email if hasattr(client, 'email') else None,
            notification_type=NotificationType.PUSH,
            event=NotificationEvent.APPOINTMENT_CONFIRMED,
            subject=subject,
            body=body,
            status=NotificationStatus.SENT if notification_sent else NotificationStatus.FAILED,
            sent_at=datetime.utcnow() if notification_sent else None,
            related_appointment_id=appointment.id,
            related_client_id=client.id,
            related_business_id=business.id
        )
        
        db.add(notification_log)
        db.commit()
        
        return {"success": True, "notification_sent": notification_sent}
        
    except Exception as e:
        logger.error(f"Error sending appointment confirmation: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

