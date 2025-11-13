"""
Authentication utilities for Firebase integration.

This module provides authentication functions for validating
Firebase tokens and extracting user information.
"""

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.credentials import get_firebase_credentials, is_development
import logging
import json
import tempfile

logger = logging.getLogger(__name__)

# Initialize Bearer token security
security = HTTPBearer()

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with credentials from environment."""
    if firebase_admin._apps:
        return  # Already initialized
    
    try:
        firebase_creds = get_firebase_credentials()
        
        # Check if we have valid credentials
        if not firebase_creds.get("project_id") or not firebase_creds.get("private_key"):
            if is_development():
                logger.warning("Firebase credentials not configured - authentication will be disabled in development")
                return
            else:
                raise ValueError("Firebase credentials are required in production")
        
        # Create credentials object from dictionary
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        if is_development():
            logger.warning(f"Firebase initialization failed in development mode: {e}")
        else:
            logger.error(f"Error initializing Firebase: {e}")
            raise

# Initialize Firebase on module import
initialize_firebase()


async def get_current_firebase_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate Firebase ID token and return user information.
    
    Args:
        credentials: HTTP Bearer credentials containing Firebase ID token
        
    Returns:
        dict: Firebase user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
        
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Firebase token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Expired Firebase token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Firebase authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_optional_firebase_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Optionally validate Firebase token for endpoints that work with/without auth.
    
    Returns:
        dict or None: Firebase user information if token is valid, None otherwise
    """
    try:
        if credentials:
            decoded_token = auth.verify_id_token(credentials.credentials)
            return decoded_token
    except Exception:
        pass
    return None