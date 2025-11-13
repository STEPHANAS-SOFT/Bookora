"""
Database configuration and session management for Bookora.

This module sets up SQLAlchemy with PostgreSQL and PostGIS support
for location-based services and provides database session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from geoalchemy2 import Geography
import logging

from app.core.credentials import get_database_url, is_development

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with PostGIS support
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    echo=is_development(),  # Log SQL queries in debug mode
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency function to get database session.
    
    This function creates a new SQLAlchemy SessionLocal that will
    be used in a single request, and then close it once the request is finished.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """
    Initialize database tables.
    Create all tables defined in the models.
    """
    try:
        # Import all models here to ensure they are registered with SQLAlchemy
        from app.models.businesses import Business, BusinessCategory, Service, BusinessHours
        from app.models.clients import Client
        from app.models.appointments import Appointment, AppointmentStatus
        from app.models.notifications import NotificationTemplate, NotificationLog
        from app.models.communications import ChatRoom, ChatMessage
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def close_db():
    """
    Close database connections.
    Called during application shutdown.
    """
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")