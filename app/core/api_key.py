"""
API Key authentication middleware for Bookora API.

This module provides API key-based authentication to secure all endpoints.
Only requests with valid API keys can access the API.
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.credentials import credentials
import logging

logger = logging.getLogger(__name__)

# Initialize Bearer token security for API key
api_key_security = HTTPBearer()


async def verify_api_key(
    auth_credentials: HTTPAuthorizationCredentials = Depends(api_key_security)
) -> str:
    """
    Verify API key from Authorization header.
    
    Expected format: Authorization: Bearer <api_key>
    """
    if not auth_credentials:
        raise HTTPException(
            status_code=401,
            detail="API key is required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    provided_key = auth_credentials.credentials
    
    # Get valid API keys from configuration
    security_config = credentials.get_security_config()
    valid_api_keys = [
        security_config.get("api_key", "bookora-dev-api-key-2025"),
        "bookora-api-key-production",  # Add production keys here
        "bookora-dev-api-key-2025"     # Development key
    ]
    
    if provided_key not in valid_api_keys:
        logger.warning(f"Invalid API key attempt: {provided_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return provided_key


async def get_current_user_with_api_key(
    api_key: str = Depends(verify_api_key),
    firebase_user: dict = Depends(None)  # We'll update this
) -> dict:
    """
    Combined authentication: API key + Firebase user.
    """
    # Import here to avoid circular imports
    from app.core.auth import get_current_firebase_user
    
    # Verify Firebase user if authentication is available
    try:
        user = await get_current_firebase_user()
        return user
    except HTTPException:
        # In development, allow API key-only access
        if credentials.is_development():
            logger.info("Development mode: API key authentication only")
            return {"uid": "dev-user", "email": "dev@bookora.com"}
        raise