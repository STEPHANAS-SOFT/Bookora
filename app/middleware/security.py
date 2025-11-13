"""
Secure API Key authentication middleware for Bookora API.

This module provides centralized API key authentication that automatically
applies to all routes without manual dependency injection.
"""

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import secrets
import logging
import hashlib
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce API key authentication on all routes.
    
    Automatically validates API keys without requiring manual dependency injection
    on each endpoint. Provides centralized security enforcement.
    """
    
    def __init__(self, app, excluded_paths: Optional[List[str]] = None):
        super().__init__(app)
        # Paths that don't require API key (health checks, docs, etc.)
        self.excluded_paths = excluded_paths or [
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/health",
            "/",
            "/api/v1/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process each request and validate API key."""
        
        # Skip API key validation for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Extract and validate API key
        try:
            api_key = self._extract_api_key(request)
            if not self._validate_api_key(api_key):
                return self._unauthorized_response()
            
            # Add validated API key to request state for use in endpoints
            request.state.api_key = api_key
            
        except HTTPException as e:
            return self._unauthorized_response(e.detail)
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return self._unauthorized_response("Authentication failed")
        
        # Proceed with the request
        response = await call_next(request)
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from API key validation."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _extract_api_key(self, request: Request) -> str:
        """Extract API key from Authorization header."""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="API key required. Include 'Authorization: Bearer <your-api-key>' header."
            )
        
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization format. Use 'Bearer <api-key>'"
            )
        
        return auth_header.replace("Bearer ", "").strip()
    
    def _validate_api_key(self, provided_key: str) -> bool:
        """
        Validate API key using secure comparison.
        
        Uses constant-time comparison to prevent timing attacks.
        """
        if not provided_key:
            return False
        
        # Get valid API keys from configuration
        valid_keys = self._get_valid_api_keys()
        
        # Use secrets.compare_digest for constant-time comparison
        for valid_key in valid_keys:
            if secrets.compare_digest(provided_key, valid_key):
                return True
        
        # Log failed attempts for monitoring
        logger.warning(
            f"Invalid API key attempt from IP: {self._get_client_ip()} "
            f"Key prefix: {provided_key[:8]}..."
        )
        return False
    
    def _get_valid_api_keys(self) -> List[str]:
        """Get list of valid API keys from secure configuration."""
        keys = []
        
        # Primary API key from settings
        if hasattr(settings, 'API_KEY') and settings.API_KEY:
            keys.append(settings.API_KEY)
        
        # Additional keys for different environments/clients
        if hasattr(settings, 'ADDITIONAL_API_KEYS'):
            additional = getattr(settings, 'ADDITIONAL_API_KEYS', '')
            if additional:
                keys.extend([key.strip() for key in additional.split(',') if key.strip()])
        
        # Fallback development key (only if no other keys configured)
        if not keys and settings.ENVIRONMENT == "development":
            logger.warning("Using fallback development API key - configure proper keys for production!")
            keys.append("bookora-dev-api-key-2025")
        
        return keys
    
    def _get_client_ip(self) -> str:
        """Get client IP address for logging."""
        # This is a simplified version - in production you'd handle X-Forwarded-For etc.
        return "unknown"
    
    def _unauthorized_response(self, detail: str = "Invalid or missing API key") -> JSONResponse:
        """Return standardized unauthorized response."""
        return JSONResponse(
            status_code=401,
            content={
                "detail": detail,
                "error_code": "INVALID_API_KEY",
                "message": "Valid API key required for access"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


class APIKeyBearer(HTTPBearer):
    """
    Optional dependency for endpoints that need the API key value.
    
    Use this only if you need the actual API key value in your endpoint.
    The middleware already validates it.
    """
    
    async def __call__(self, request: Request) -> str:
        """Return the validated API key from request state."""
        # API key already validated by middleware
        if hasattr(request.state, 'api_key'):
            return request.state.api_key
        
        # Fallback if middleware not used (shouldn't happen)
        credentials = await super().__call__(request)
        return credentials.credentials if credentials else None


# Instance for use in endpoints if needed
api_key_bearer = APIKeyBearer()


def get_api_key(request: Request) -> str:
    """
    Dependency to get the validated API key in endpoints.
    
    Use this if you need the API key value in your endpoint logic.
    """
    if hasattr(request.state, 'api_key'):
        return request.state.api_key
    
    raise HTTPException(
        status_code=500,
        detail="API key not found in request state"
    )