"""
FastAPI application entry point for Bookora.

Multi-tenant appointment booking system with DDD/CQRS architecture.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.credentials import credentials
from app.core.database import engine
from app.api.v1.api import api_router
from app.websocket.connection_manager import connection_manager
from app.middleware.security import APIKeyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting Bookora API...")
    yield
    # Shutdown
    print("🛑 Shutting down Bookora API...")


# Create FastAPI application
app = FastAPI(
    title="Bookora API",
    description="Multi-tenant appointment booking system API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
    root_path="/bookora"
)

# Get CORS configuration
cors_config = credentials.get_cors_config()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=cors_config["allowed_hosts"]
)

# Add API key security middleware - This must be added AFTER other middleware
app.add_middleware(
    APIKeyMiddleware,
    excluded_paths=[
        "/", 
        "/docs", 
        "/redoc", 
        "/openapi.json",
        "/api/v1/openapi.json",
        "/health"
    ]
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Bookora API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "bookora-api"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )