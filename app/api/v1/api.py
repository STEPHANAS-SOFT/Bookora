"""
Main API router for version 1 of the Bookora API.

This module combines all API endpoints and includes WebSocket
routes for real-time chat functionality.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    clients, 
    businesses, 
    appointments,
    communications,
    notifications,
    staff,
    reviews,
    favorites,
    services,
    websocket,
    business_hours
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(communications.router, prefix="/communications", tags=["communications"])  
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
api_router.include_router(business_hours.router, prefix="/business-hours", tags=["business-hours"])