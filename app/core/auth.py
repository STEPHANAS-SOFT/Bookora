"""
Authentication utilities for Bookora API.

This module provides simple authentication functions.
Firebase UID is passed as parameter from frontend, no token validation.
Only API key authentication is used (handled by middleware).
"""

from fastapi import HTTPException, Query
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_firebase_uid_param(firebase_uid: str = Query(..., description="Firebase UID from frontend authentication")) -> str:
    """
    Get Firebase UID from query parameter.
    
    Args:
        firebase_uid: Firebase UID passed from frontend
        
    Returns:
        str: Firebase UID for database queries
        
    Raises:
        HTTPException: If firebase_uid is empty or invalid
    """
    if not firebase_uid or not firebase_uid.strip():
        raise HTTPException(
            status_code=400,
            detail="Firebase UID is required"
        )
    
    if len(firebase_uid.strip()) < 10:  # Basic validation
        raise HTTPException(
            status_code=400,
            detail="Invalid Firebase UID format"
        )
    
    return firebase_uid.strip()


def get_optional_firebase_uid_param(firebase_uid: Optional[str] = Query(None, description="Optional Firebase UID")) -> Optional[str]:
    """
    Get optional Firebase UID from query parameter.
    
    Args:
        firebase_uid: Optional Firebase UID passed from frontend
        
    Returns:
        Optional[str]: Firebase UID or None
    """
    if firebase_uid and firebase_uid.strip():
        return firebase_uid.strip()
    return None


# For backward compatibility - remove Firebase token validation
async def get_current_firebase_user() -> dict:
    """
    Deprecated: This function is no longer used.
    Firebase authentication is handled on the frontend.
    Use firebase_uid parameter instead.
    """
    raise HTTPException(
        status_code=501,
        detail="Firebase authentication is handled on frontend. Pass firebase_uid as parameter."
    )