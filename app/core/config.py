"""
Configuration settings for Bookora FastAPI application.

This module contains all configuration settings using Pydantic Settings
for environment variable management and validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
import os
import secrets
from pathlib import Path


class Settings(BaseSettings):
    """
    Centralized configuration management for Bookora API.
    
    All settings are loaded from environment variables with sensible defaults.
    This is the single source of truth for all application configuration.
    """
    
    # Project Information
    PROJECT_NAME: str = "Bookora API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Multi-tenant appointment booking system"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    TESTING: bool = Field(default=False, env="TESTING")
    
    # Security Configuration
    SECRET_KEY: str = Field(env="SECRET_KEY")
    API_KEY: str = Field(default="bookora-dev-api-key-2025", env="API_KEY")
    ADDITIONAL_API_KEYS: str = Field(default="", env="ADDITIONAL_API_KEYS")  # Comma-separated additional keys
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM") 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Server Configuration
    SERVER_HOST: str = Field(default="localhost", env="SERVER_HOST")
    SERVER_PORT: int = Field(default=8000, env="SERVER_PORT")
    
    # CORS & Host Configuration
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080", env="CORS_ORIGINS")
    ALLOWED_HOSTS: str = Field(default="localhost,127.0.0.1,0.0.0.0", env="ALLOWED_HOSTS")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Convert allowed hosts string to list."""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(',') if host.strip()]
    
    # Database Configuration
    DATABASE_URL: str = Field(env="DATABASE_URL")
    DATABASE_USER: str = Field(env="DATABASE_USER") 
    DATABASE_PASSWORD: str = Field(env="DATABASE_PASSWORD")
    DATABASE_HOST: str = Field(default="localhost", env="DATABASE_HOST")
    DATABASE_PORT: int = Field(default=5432, env="DATABASE_PORT")
    DATABASE_NAME: str = Field(env="DATABASE_NAME")
    
    # Redis Configuration (for Celery and WebSocket)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = Field(default="", env="FIREBASE_PROJECT_ID")
    FIREBASE_PRIVATE_KEY_ID: str = Field(default="", env="FIREBASE_PRIVATE_KEY_ID")
    FIREBASE_PRIVATE_KEY: str = Field(default="", env="FIREBASE_PRIVATE_KEY")
    FIREBASE_CLIENT_EMAIL: str = Field(default="", env="FIREBASE_CLIENT_EMAIL")
    FIREBASE_CLIENT_ID: str = Field(default="", env="FIREBASE_CLIENT_ID")
    FIREBASE_AUTH_URI: str = Field(default="https://accounts.google.com/o/oauth2/auth", env="FIREBASE_AUTH_URI")
    FIREBASE_TOKEN_URI: str = Field(default="https://oauth2.googleapis.com/token", env="FIREBASE_TOKEN_URI")
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL: str = Field(default="https://www.googleapis.com/oauth2/v1/certs", env="FIREBASE_AUTH_PROVIDER_X509_CERT_URL")
    FIREBASE_CLIENT_X509_CERT_URL: str = Field(default="", env="FIREBASE_CLIENT_X509_CERT_URL")
    
    @property
    def firebase_credentials(self) -> Dict[str, Any]:
        """Build Firebase credentials dictionary from environment variables."""
        return {
            "type": "service_account",
            "project_id": self.FIREBASE_PROJECT_ID,
            "private_key_id": self.FIREBASE_PRIVATE_KEY_ID,
            "private_key": self.FIREBASE_PRIVATE_KEY.replace('\\n', '\n') if self.FIREBASE_PRIVATE_KEY else "",
            "client_email": self.FIREBASE_CLIENT_EMAIL,
            "client_id": self.FIREBASE_CLIENT_ID,
            "auth_uri": self.FIREBASE_AUTH_URI,
            "token_uri": self.FIREBASE_TOKEN_URI,
            "auth_provider_x509_cert_url": self.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": self.FIREBASE_CLIENT_X509_CERT_URL
        }
    
    # FCM Configuration (HTTP v1 API)
    FCM_SENDER_ID: str = Field(default="", env="FCM_SENDER_ID")
    FCM_PROJECT_ID: str = Field(default="", env="FCM_PROJECT_ID")  # Usually same as FIREBASE_PROJECT_ID
    
    # Email Configuration (SMTP)
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: str = Field(default="", env="SMTP_USERNAME")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    FROM_EMAIL: str = Field(default="", env="FROM_EMAIL")
    FROM_NAME: str = Field(default="Bookora", env="FROM_NAME")
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    UPLOAD_DIR: str = Field(default="uploads/", env="UPLOAD_DIR")
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    
    # Timezone Configuration
    DEFAULT_TIMEZONE: str = Field(default="UTC", env="DEFAULT_TIMEZONE")
    TIMEZONE: str = Field(default="UTC", env="TIMEZONE")  # For Celery
    
    # Business Logic Configuration
    DEFAULT_APPOINTMENT_DURATION: int = 30  # minutes
    MAX_ADVANCE_BOOKING_DAYS: int = 90  # days
    MIN_ADVANCE_BOOKING_HOURS: int = 2  # hours
    APPOINTMENT_REMINDER_HOURS: List[int] = [24, 2]  # Send reminders 24h and 2h before
    
    # Location Configuration
    DEFAULT_SEARCH_RADIUS_KM: float = 50.0
    MAX_SEARCH_RADIUS_KM: float = 100.0
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()