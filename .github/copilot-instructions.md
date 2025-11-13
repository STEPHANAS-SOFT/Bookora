<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Bookora - Multi-Tenant Appointment Booking API

This is a Django REST API project for Bookora, a multi-tenant appointment booking system where:
- Business owners (Hair Salons, etc.) can register and manage appointments
- Clients can book appointments, chat, and call businesses
- Automatic push notifications and email reminders
- Location-based business discovery
- Firebase authentication and FCM notifications
- PostgreSQL database with pgAdmin4

## Architecture
- Domain-Driven Design (DDD)
- Command Query Responsibility Segregation (CQRS)
- Multi-tenant architecture
- RESTful API endpoints

## Key Features
- Firebase UID-based authentication for businesses and clients
- FCM token management for push notifications
- Location-based services with latitude/longitude
- Appointment scheduling with conflict prevention
- Chat and call functionality
- Email and push notification reminders
- Business discovery and booking links