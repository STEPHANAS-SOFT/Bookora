"""
Security middleware for API key authentication.

This module provides middleware for API key-based authentication
for the Bookora REST API.
"""

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time

from app.core.config import settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    Validates API key for all requests except health check and docs.
    """
    
    # Endpoints that don't require API key authentication
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/openapi.json",
        "/"
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and validate API key."""
        
        # Skip authentication for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get API key from headers
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "API key required",
                    "message": "Please provide a valid API key in the X-API-Key header"
                }
            )
        
        # Validate API key
        if api_key != settings.API_KEY:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Invalid API key",
                    "message": "The provided API key is invalid"
                }
            )
        
        # API key is valid, proceed with request
        response = await call_next(request)
        return response


# Alternative function-based approach for dependency injection
security = HTTPBearer()


async def get_api_key(api_key: str = None) -> str:
    """
    Validate API key using dependency injection.
    
    Args:
        api_key: API key from request header
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )
    
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return api_key