"""
Centralized credentials and configuration management for Bookora.

This module provides a single source of truth for all application credentials
and configuration, making it easy to access them from anywhere in the application.
"""

from typing import Dict, Any, Optional
import json
import tempfile
import os
from pathlib import Path

from app.core.config import settings


class CredentialsManager:
    """
    Centralized credentials manager for the Bookora application.
    
    This class provides methods to access credentials and configuration
    in a secure and consistent way across the application.
    """
    
    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": settings.DATABASE_URL,
            "host": settings.DATABASE_HOST,
            "port": settings.DATABASE_PORT,
            "name": settings.DATABASE_NAME,
            "user": settings.DATABASE_USER,
            "password": settings.DATABASE_PASSWORD,
        }
    
    @staticmethod
    def get_redis_config() -> Dict[str, str]:
        """Get Redis configuration."""
        return {
            "url": settings.REDIS_URL,
        }
    
    @staticmethod
    def get_firebase_credentials() -> Dict[str, Any]:
        """
        Get Firebase credentials as a dictionary.
        
        Returns the Firebase service account credentials needed for
        Firebase Admin SDK initialization.
        """
        return settings.firebase_credentials
    
    @staticmethod
    def get_firebase_credentials_file() -> str:
        """
        Create a temporary Firebase credentials file.
        
        This is useful when Firebase SDK requires a file path instead of
        a credentials dictionary.
        
        Returns:
            str: Path to temporary credentials file
        """
        credentials = CredentialsManager.get_firebase_credentials()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        )
        
        try:
            json.dump(credentials, temp_file, indent=2)
            temp_file.flush()
            return temp_file.name
        finally:
            temp_file.close()
    
    @staticmethod
    def get_fcm_config() -> Dict[str, str]:
        """Get FCM (Firebase Cloud Messaging) configuration."""
        return {
            "server_key": settings.FCM_SERVER_KEY,
        }
    
    @staticmethod
    def get_email_config() -> Dict[str, Any]:
        """Get email/SMTP configuration."""
        return {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "username": settings.SMTP_USERNAME,
            "password": settings.SMTP_PASSWORD,
            "from_email": settings.FROM_EMAIL,
            "from_name": settings.FROM_NAME,
        }
    
    @staticmethod
    def get_security_config() -> Dict[str, str]:
        """Get security configuration including API keys."""
        return {
            "api_key": getattr(settings, 'API_KEY', 'bookora-dev-api-key-2025'),
            "jwt_secret": getattr(settings, 'JWT_SECRET_KEY', 'your-secret-key-here'),
        }
    
    @staticmethod
    def get_cors_config() -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "origins": settings.cors_origins_list,
            "allowed_hosts": settings.allowed_hosts_list,
        }
    
    @staticmethod
    def get_file_upload_config() -> Dict[str, Any]:
        """Get file upload configuration."""
        return {
            "max_size": settings.MAX_FILE_SIZE,
            "upload_dir": settings.UPLOAD_DIR,
            "allowed_types": settings.ALLOWED_FILE_TYPES,
        }
    
    @staticmethod
    def get_security_config() -> Dict[str, Any]:
        """Get security configuration."""
        return {
            "secret_key": settings.SECRET_KEY,
            "algorithm": settings.ALGORITHM,
            "token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        }
    
    @staticmethod
    def get_business_config() -> Dict[str, Any]:
        """Get business logic configuration."""
        return {
            "default_appointment_duration": settings.DEFAULT_APPOINTMENT_DURATION,
            "max_advance_booking_days": settings.MAX_ADVANCE_BOOKING_DAYS,
            "min_advance_booking_hours": settings.MIN_ADVANCE_BOOKING_HOURS,
            "reminder_hours": settings.APPOINTMENT_REMINDER_HOURS,
            "default_search_radius": settings.DEFAULT_SEARCH_RADIUS_KM,
            "max_search_radius": settings.MAX_SEARCH_RADIUS_KM,
        }
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode."""
        return settings.DEBUG and settings.ENVIRONMENT.lower() == "development"
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production mode."""
        return not settings.DEBUG and settings.ENVIRONMENT.lower() == "production"
    
    @staticmethod
    def is_testing() -> bool:
        """Check if running in testing mode."""
        return settings.TESTING
    
    @staticmethod
    def cleanup_temp_files():
        """Clean up any temporary files created by this manager."""
        # This could be enhanced to track and clean up temp Firebase credential files
        pass


# Global credentials manager instance
credentials = CredentialsManager()


# Convenience functions for common operations
def get_database_url() -> str:
    """Get database URL."""
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL."""
    return settings.REDIS_URL


def get_firebase_credentials() -> Dict[str, Any]:
    """Get Firebase credentials."""
    return credentials.get_firebase_credentials()


def get_email_config() -> Dict[str, Any]:
    """Get email configuration."""
    return credentials.get_email_config()


def is_development() -> bool:
    """Check if in development mode."""
    return credentials.is_development()


def is_production() -> bool:
    """Check if in production mode."""
    return credentials.is_production()