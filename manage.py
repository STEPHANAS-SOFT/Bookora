#!/usr/bin/env python3
"""
Bookora Management CLI Script.

This script provides command-line utilities for managing the Bookora backend:
- Database operations (migrations, seeding, cleanup)
- User management (create, delete, list)
- Task management (run background tasks manually)
- System diagnostics and health checks

Usage:
    python manage.py <command> [options]

Commands:
    db:migrate          - Run database migrations
    db:seed             - Seed database with sample data
    db:reset            - Reset database (WARNING: Deletes all data)
    db:backup           - Create database backup
    
    user:create-client  - Create a new client account
    user:create-business - Create a new business account
    user:list           - List all users
    
    task:send-reminders - Manually trigger appointment reminders
    task:cleanup        - Run database cleanup tasks
    task:stats          - Generate statistics report
    
    health:check        - Run system health check
    health:db           - Check database health
    
    celery:worker       - Start Celery worker
    celery:beat         - Start Celery beat scheduler
    celery:flower       - Start Celery Flower monitoring UI

Author: Bookora Team
"""

import sys
import argparse
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def db_migrate():
    """Run database migrations using Alembic."""
    print("🔄 Running database migrations...")
    import subprocess
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Migrations completed successfully")
        print(result.stdout)
    else:
        print("❌ Migration failed")
        print(result.stderr)
        sys.exit(1)


def db_seed():
    """Seed database with sample data for development/testing."""
    print("🌱 Seeding database with sample data...")
    
    from app.core.database import SessionLocal
    from app.models.businesses import Business, BusinessCategory, Service
    from app.models.clients import Client
    import uuid
    
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_clients = db.query(Client).count()
        if existing_clients > 0:
            response = input(f"⚠️  Database already contains {existing_clients} clients. Continue seeding? (y/N): ")
            if response.lower() != 'y':
                print("Seeding cancelled.")
                return
        
        # Create sample business categories
        categories_data = [
            {"name": "Hair Salon", "description": "Hair styling and treatment services"},
            {"name": "Spa & Wellness", "description": "Spa and wellness services"},
            {"name": "Dental Clinic", "description": "Dental care services"},
            {"name": "Medical Clinic", "description": "Medical consultation services"},
        ]
        
        categories = []
        for cat_data in categories_data:
            category = db.query(BusinessCategory).filter(
                BusinessCategory.name == cat_data["name"]
            ).first()
            
            if not category:
                category = BusinessCategory(**cat_data)
                db.add(category)
                categories.append(category)
                print(f"  ✓ Created category: {cat_data['name']}")
            else:
                categories.append(category)
                print(f"  → Category already exists: {cat_data['name']}")
        
        db.commit()
        
        # Create sample clients
        sample_clients = [
            {
                "firebase_uid": f"test_client_{uuid.uuid4().hex[:8]}",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "profile_image_url": "https://example.com/avatar1.jpg"
            },
            {
                "firebase_uid": f"test_client_{uuid.uuid4().hex[:8]}",
                "first_name": "Jane",
                "last_name": "Smith",
                "phone_number": "+1234567891",
                "profile_image_url": "https://example.com/avatar2.jpg"
            },
        ]
        
        for client_data in sample_clients:
            client = Client(**client_data)
            db.add(client)
            print(f"  ✓ Created client: {client_data['first_name']} {client_data['last_name']}")
        
        # Create sample businesses
        sample_businesses = [
            {
                "firebase_uid": f"test_business_{uuid.uuid4().hex[:8]}",
                "name": "Elegant Hair Studio",
                "description": "Premium hair styling and treatments",
                "phone_number": "+1234567892",
                "email": "contact@eleganthair.com",
                "address": "123 Main St, City",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "category_id": categories[0].id if categories else None,
                "logo_url": "https://example.com/logo1.jpg",
                "is_approved": True
            },
            {
                "firebase_uid": f"test_business_{uuid.uuid4().hex[:8]}",
                "name": "Tranquility Spa",
                "description": "Relaxation and wellness services",
                "phone_number": "+1234567893",
                "email": "info@tranquilityspa.com",
                "address": "456 Oak Ave, City",
                "latitude": 40.7589,
                "longitude": -73.9851,
                "category_id": categories[1].id if len(categories) > 1 else None,
                "logo_url": "https://example.com/logo2.jpg",
                "is_approved": True
            },
        ]
        
        for business_data in sample_businesses:
            business = Business(**business_data)
            db.add(business)
            db.flush()  # Get the business ID
            
            # Add sample services for each business
            if "Hair" in business.name:
                services = [
                    {"name": "Haircut", "price": 35.00, "duration_minutes": 30},
                    {"name": "Hair Coloring", "price": 85.00, "duration_minutes": 90},
                    {"name": "Styling", "price": 45.00, "duration_minutes": 45},
                ]
            else:
                services = [
                    {"name": "Massage Therapy", "price": 75.00, "duration_minutes": 60},
                    {"name": "Facial Treatment", "price": 65.00, "duration_minutes": 45},
                    {"name": "Aromatherapy", "price": 55.00, "duration_minutes": 30},
                ]
            
            for service_data in services:
                service = Service(
                    business_id=business.id,
                    **service_data
                )
                db.add(service)
            
            print(f"  ✓ Created business: {business_data['name']} with {len(services)} services")
        
        db.commit()
        print("\n✅ Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Seeding failed: {e}")
        logger.error(f"Seeding error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


def db_reset():
    """Reset database (WARNING: Deletes all data)."""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    response = input("Are you sure you want to continue? Type 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("Reset cancelled.")
        return
    
    print("🗑️  Resetting database...")
    
    from app.core.database import engine, Base
    
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("  ✓ Dropped all tables")
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        print("  ✓ Recreated all tables")
        
        print("\n✅ Database reset complete!")
        print("💡 Run 'python manage.py db:seed' to populate with sample data")
        
    except Exception as e:
        print(f"\n❌ Reset failed: {e}")
        logger.error(f"Reset error: {e}", exc_info=True)
        sys.exit(1)


def task_send_reminders():
    """Manually trigger appointment reminder task."""
    print("📧 Sending appointment reminders...")
    
    from app.tasks.appointment_tasks import check_and_send_reminders
    
    try:
        result = check_and_send_reminders()
        print(f"\n✅ Reminders sent successfully!")
        print(f"  • 24h reminders: {result.get('24h', 0)}")
        print(f"  • 2h reminders: {result.get('2h', 0)}")
        print(f"  • Errors: {result.get('errors', 0)}")
    except Exception as e:
        print(f"\n❌ Failed to send reminders: {e}")
        logger.error(f"Reminder error: {e}", exc_info=True)
        sys.exit(1)


def task_cleanup():
    """Run database cleanup tasks."""
    print("🧹 Running database cleanup...")
    
    from app.tasks.maintenance_tasks import (
        cleanup_old_notifications,
        cleanup_expired_appointments,
        cleanup_stale_chatrooms
    )
    
    try:
        print("\n  Cleaning up notifications...")
        notif_result = cleanup_old_notifications()
        print(f"    ✓ Deleted {notif_result.get('total_deleted', 0)} old notifications")
        
        print("\n  Cleaning up appointments...")
        appt_result = cleanup_expired_appointments()
        print(f"    ✓ Archived {appt_result.get('archived_count', 0)} old appointments")
        
        print("\n  Cleaning up chat rooms...")
        chat_result = cleanup_stale_chatrooms()
        print(f"    ✓ Archived {chat_result.get('archived_count', 0)} stale chat rooms")
        
        print("\n✅ Cleanup complete!")
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        logger.error(f"Cleanup error: {e}", exc_info=True)
        sys.exit(1)


def task_stats():
    """Generate and display statistics report."""
    print("📊 Generating statistics...")
    
    from app.tasks.maintenance_tasks import generate_daily_statistics
    
    try:
        stats = generate_daily_statistics()
        
        print("\n📈 Statistics Report")
        print("=" * 50)
        print(f"Date: {stats.get('date', 'N/A')}")
        
        if 'appointments' in stats:
            print(f"\n📅 Appointments:")
            print(f"  Total: {stats['appointments'].get('total', 0)}")
            print(f"  Completed: {stats['appointments'].get('completed', 0)}")
            print(f"  Cancelled: {stats['appointments'].get('cancelled', 0)}")
            print(f"  Pending: {stats['appointments'].get('pending', 0)}")
        
        if 'users' in stats:
            print(f"\n👥 Users:")
            print(f"  New clients: {stats['users'].get('new_clients', 0)}")
            print(f"  Total clients: {stats['users'].get('total_clients', 0)}")
        
        if 'businesses' in stats:
            print(f"\n🏢 Businesses:")
            print(f"  New registrations: {stats['businesses'].get('new_registrations', 0)}")
            print(f"  Total active: {stats['businesses'].get('total_active', 0)}")
        
        if 'reviews' in stats:
            print(f"\n⭐ Reviews:")
            print(f"  New reviews: {stats['reviews'].get('new_reviews', 0)}")
            print(f"  Total reviews: {stats['reviews'].get('total_reviews', 0)}")
            print(f"  Average rating: {stats['reviews'].get('average_rating', 0)}")
        
        print("\n✅ Statistics generated successfully!")
        
    except Exception as e:
        print(f"\n❌ Failed to generate statistics: {e}")
        logger.error(f"Statistics error: {e}", exc_info=True)
        sys.exit(1)


def health_check():
    """Run comprehensive system health check."""
    print("🏥 Running system health check...")
    
    from app.tasks.maintenance_tasks import check_database_health
    
    try:
        health = check_database_health()
        
        print(f"\n📋 Health Check Report")
        print("=" * 50)
        print(f"Status: {health.get('status', 'unknown').upper()}")
        print(f"Timestamp: {health.get('timestamp', 'N/A')}")
        
        if 'checks' in health:
            print(f"\n🔍 Checks:")
            for check_name, check_result in health['checks'].items():
                if isinstance(check_result, dict):
                    print(f"\n  {check_name}:")
                    for key, value in check_result.items():
                        print(f"    • {key}: {value}")
                else:
                    status_icon = "✅" if check_result == "OK" else "⚠️"
                    print(f"  {status_icon} {check_name}: {check_result}")
        
        print("\n" + "=" * 50)
        
        if health.get('status') == 'healthy':
            print("✅ System is healthy!")
        elif health.get('status') == 'degraded':
            print("⚠️  System is degraded but functional")
        else:
            print("❌ System is unhealthy!")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        logger.error(f"Health check error: {e}", exc_info=True)
        sys.exit(1)


def celery_worker():
    """Start Celery worker."""
    print("🚀 Starting Celery worker...")
    import subprocess
    subprocess.run([
        "celery", "-A", "app.core.celery_app", "worker",
        "--loglevel=info",
        "--concurrency=4"
    ])


def celery_beat():
    """Start Celery beat scheduler."""
    print("⏰ Starting Celery beat scheduler...")
    import subprocess
    subprocess.run([
        "celery", "-A", "app.core.celery_app", "beat",
        "--loglevel=info"
    ])


def celery_flower():
    """Start Celery Flower monitoring UI."""
    print("🌸 Starting Celery Flower...")
    import subprocess
    subprocess.run([
        "celery", "-A", "app.core.celery_app", "flower",
        "--port=5555"
    ])


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bookora Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "command",
        help="Command to execute",
        choices=[
            "db:migrate", "db:seed", "db:reset", "db:backup",
            "user:create-client", "user:create-business", "user:list",
            "task:send-reminders", "task:cleanup", "task:stats",
            "health:check", "health:db",
            "celery:worker", "celery:beat", "celery:flower"
        ]
    )
    
    args = parser.parse_args()
    
    # Map commands to functions
    commands = {
        "db:migrate": db_migrate,
        "db:seed": db_seed,
        "db:reset": db_reset,
        "task:send-reminders": task_send_reminders,
        "task:cleanup": task_cleanup,
        "task:stats": task_stats,
        "health:check": health_check,
        "health:db": health_check,
        "celery:worker": celery_worker,
        "celery:beat": celery_beat,
        "celery:flower": celery_flower,
    }
    
    # Execute command
    if args.command in commands:
        try:
            commands[args.command]()
        except KeyboardInterrupt:
            print("\n\n⏸️  Operation cancelled by user")
            sys.exit(0)
    else:
        print(f"❌ Command '{args.command}' not implemented yet")
        sys.exit(1)


if __name__ == "__main__":
    main()

