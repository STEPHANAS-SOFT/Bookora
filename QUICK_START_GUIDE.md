# Bookora Backend - Quick Start Guide

## 🚀 Getting Started

This guide will help you get the Bookora backend up and running quickly.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ with PostGIS extension
- Virtual environment (venv)

## 📦 Installation

### 1. Activate Virtual Environment

```bash
cd /Users/apple/PostgressDB/Bookora
source venv/bin/activate
```

### 2. Install Dependencies (if needed)

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root (if not exists):

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bookora

# API Settings
API_KEY=bookora-dev-api-key-2025
ENVIRONMENT=development

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# Firebase (for FCM notifications)
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json

# SMTP (for email notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🗄️ Database Setup

### 1. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and enable PostGIS
CREATE DATABASE bookora;
\c bookora
CREATE EXTENSION IF NOT EXISTS postgis;
\q
```

### 2. Create Database Migration

```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## ▶️ Running the Application

### Development Server

```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate

# Run with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Production Server

```bash
# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🧪 Testing the API

### Health Check

```bash
curl http://localhost:8000/health
```

### Testing with API Key

All endpoints (except health and docs) require the API key in the header:

```bash
curl -X GET "http://localhost:8000/api/v1/businesses/categories" \
  -H "X-API-Key: bookora-dev-api-key-2025"
```

### Example: Register a Client

```bash
curl -X POST "http://localhost:8000/api/v1/clients/register" \
  -H "X-API-Key: bookora-dev-api-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_uid": "test-user-123",
    "email": "client@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890"
  }'
```

### Example: Register a Business

```bash
curl -X POST "http://localhost:8000/api/v1/businesses/register?firebase_uid=test-business-123" \
  -H "X-API-Key: bookora-dev-api-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Best Hair Salon",
    "description": "Professional hair care services",
    "email": "business@example.com",
    "category_id": "category-uuid-here",
    "business_phone": "+1234567890",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "postal_code": "10001"
  }'
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

The interactive documentation allows you to:
- View all available endpoints
- Test endpoints directly from the browser
- See request/response schemas
- Understand authentication requirements

## 🔑 Authentication

### API Key Authentication

All requests must include the API key:

```http
X-API-Key: bookora-dev-api-key-2025
```

### User Identification

User-specific endpoints require the Firebase UID as a query parameter:

```http
GET /api/v1/clients/profile?firebase_uid=user-uid-here
```

## 📁 Project Structure

```
Bookora/
├── app/
│   ├── api/v1/endpoints/    # API endpoint routes
│   ├── core/                # Core configurations
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   └── main.py              # Application entry point
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── venv/                    # Virtual environment
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
└── alembic.ini             # Alembic configuration
```

## 🛠️ Common Commands

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Database Connection Issues

1. Check PostgreSQL is running: `pg_isready`
2. Verify connection string in `.env`
3. Ensure database exists: `psql -l`

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### PostGIS Not Found

```bash
# Install PostGIS (macOS)
brew install postgis

# Install PostGIS (Ubuntu)
sudo apt-get install postgis postgresql-12-postgis-3
```

## 📋 Available Endpoints

### Core Endpoints
- **Health**: `GET /health`
- **Root**: `GET /`

### Business Endpoints
- `GET /api/v1/businesses/categories` - Get business categories
- `POST /api/v1/businesses/register` - Register new business
- `GET /api/v1/businesses/me` - Get own business profile
- `PUT /api/v1/businesses/me` - Update business profile
- `GET /api/v1/businesses/search` - Search businesses
- `GET /api/v1/businesses/{business_id}` - Get business details
- `GET /api/v1/businesses/{business_id}/services` - Get business services
- `POST /api/v1/businesses/me/services` - Create service
- `PUT /api/v1/businesses/me/services/{service_id}` - Update service
- `DELETE /api/v1/businesses/me/services/{service_id}` - Delete service

### Client Endpoints
- `POST /api/v1/clients/register` - Register new client
- `GET /api/v1/clients/profile` - Get client profile
- `PUT /api/v1/clients/profile` - Update client profile
- `DELETE /api/v1/clients/profile` - Delete client profile
- `PUT /api/v1/clients/fcm-token` - Update FCM token

### Appointment Endpoints
- `POST /api/v1/appointments/book` - Book appointment
- `GET /api/v1/appointments/my-appointments` - Get user appointments
- `GET /api/v1/appointments/{appointment_id}` - Get appointment details
- `PUT /api/v1/appointments/{appointment_id}/status` - Update status
- `PUT /api/v1/appointments/{appointment_id}/reschedule` - Reschedule
- `GET /api/v1/appointments/business/calendar` - Business calendar view

### Communication Endpoints
- `GET /api/v1/communications/chat-rooms` - Get chat rooms
- `GET /api/v1/communications/chat-rooms/{room_id}/messages` - Get messages
- `POST /api/v1/communications/chat-rooms` - Create chat room
- `POST /api/v1/communications/chat-rooms/{room_id}/messages` - Send message
- `PUT /api/v1/communications/chat-rooms/{room_id}/messages/{message_id}/read` - Mark read

### Notification Endpoints
- `GET /api/v1/notifications/` - Get notifications
- `GET /api/v1/notifications/preferences` - Get preferences
- `PUT /api/v1/notifications/preferences/{event}` - Update preference
- `PUT /api/v1/notifications/fcm-token` - Update FCM token
- `GET /api/v1/notifications/unread-count` - Get unread count

## 🌐 Frontend Integration

### API Base URL
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

### Making Requests
```javascript
const response = await fetch(`${API_BASE_URL}/clients/profile?firebase_uid=${uid}`, {
  method: 'GET',
  headers: {
    'X-API-Key': 'bookora-dev-api-key-2025',
    'Content-Type': 'application/json'
  }
});
```

## 📞 Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review the implementation summary: `BACKEND_IMPLEMENTATION_SUMMARY.md`
3. Check logs for detailed error messages

## 🎉 You're Ready!

The Bookora backend is now running and ready to serve requests. Start building your frontend integration or use the API documentation to explore available endpoints.

Happy coding! 🚀

