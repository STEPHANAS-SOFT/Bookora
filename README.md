# Bookora - Multi-Tenant Appointment Booking API

![Python](https://img.shields.io/badge/python-v3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A comprehensive REST API for multi-tenant appointment booking system built with FastAPI, following Domain-Driven Design (DDD) and CQRS patterns.

## 🚀 Features

- **Multi-Tenant Architecture**: Separate business and client domains
- **Real-time Chat**: WebSocket-based messaging between clients and businesses
- **API Key Authentication**: Secure API access with Firebase UID parameters
- **Location-Based Services**: PostgreSQL with PostGIS for proximity searches
- **Push Notifications**: FCM integration for mobile notifications
- **Email Notifications**: SMTP-based email reminders and notifications
- **Appointment Management**: Complete booking lifecycle with conflict prevention
- **Timezone Support**: Business-specific timezone handling
- **DDD/CQRS Pattern**: Clean architecture with domain separation

## 🏗️ Architecture

```
bookora/
├── app/
│   ├── api/v1/endpoints/     # API route handlers
│   ├── core/                 # Core configuration and utilities
│   ├── models/               # Database models (Domain entities)
│   ├── schemas/              # Pydantic schemas (DTOs)
│   └── websocket/            # WebSocket connection management
├── alembic/                  # Database migrations
├── tests/                    # Test suite
└── main.py                   # FastAPI application entry point
```

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with PostGIS
- **ORM**: SQLAlchemy
- **Authentication**: API Key + Firebase UID parameters
- **Real-time**: WebSockets
- **Task Queue**: Celery + Redis
- **Migrations**: Alembic
- **Testing**: pytest
- **Documentation**: OpenAPI/Swagger

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 13+ with PostGIS extension
- Redis (for Celery)
- Firebase project with service account

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd Bookora
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Configure the following variables:

```env
# Database
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your-password
DB_NAME=bookora
DB_PORT=5432

# Firebase
FIREBASE_CREDENTIALS_PATH=path/to/your/firebase-service-account.json

# Email (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Redis
REDIS_URL=redis://localhost:6379/0

# FCM
FCM_SERVER_KEY=your-fcm-server-key
```

### 4. Database Setup

```bash
# Create database
createdb bookora

# Enable PostGIS extension
psql -d bookora -c "CREATE EXTENSION postgis;"

# Run migrations
alembic upgrade head
```

### 5. Run the Application

#### Development Mode
```bash
# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using VS Code task (Ctrl+Shift+P -> "Tasks: Run Task" -> "Start FastAPI Server")
```

#### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Main API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 API Documentation

### Business Endpoints
- `POST /api/v1/businesses/register` - Register new business
- `GET /api/v1/businesses/me` - Get current business profile
- `PUT /api/v1/businesses/me` - Update business profile
- `GET /api/v1/businesses/search` - Search businesses by location/category
- `POST /api/v1/businesses/me/services` - Create business service
- `GET /api/v1/businesses/{id}/services` - Get business services

### Client Endpoints
- `POST /api/v1/clients/register` - Register new client
- `GET /api/v1/clients/me` - Get current client profile
- `PUT /api/v1/clients/me` - Update client profile

### Appointment Endpoints
- `POST /api/v1/appointments/book` - Book new appointment
- `GET /api/v1/appointments/my-appointments` - Get user appointments
- `PUT /api/v1/appointments/{id}/reschedule` - Reschedule appointment
- `DELETE /api/v1/appointments/{id}/cancel` - Cancel appointment

### Communication Endpoints
- `GET /api/v1/communications/chat-rooms` - Get user chat rooms
- `GET /api/v1/communications/chat-rooms/{id}/messages` - Get chat messages

### WebSocket Endpoints
- `WS /api/v1/ws/chat/{firebase_uid}` - Real-time chat connection

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_main.py -v
```

## 🚀 Deployment

### Using Docker (Recommended)

```bash
# Build image
docker build -t bookora-api .

# Run with docker-compose
docker-compose up -d
```

### Manual Deployment

1. Set up PostgreSQL with PostGIS
2. Configure environment variables
3. Run migrations: `alembic upgrade head`
4. Start application: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Start Celery worker: `celery -A app.core.celery worker --loglevel=info`

## 🔧 Development

### VS Code Setup

The project includes VS Code configuration with:
- Python interpreter setup
- Debug configurations
- Tasks for common operations
- Recommended extensions

### Adding New Features

1. **Models**: Add to `app/models/`
2. **Schemas**: Add to `app/schemas/`
3. **Endpoints**: Add to `app/api/v1/endpoints/`
4. **Tests**: Add to `tests/`
5. **Migration**: `alembic revision --autogenerate -m "Description"`

## 🏢 Business Categories

Pre-defined categories (admin-managed):
- Hair Salons
- Spas & Wellness
- Dental Clinics
- Medical Clinics
- Beauty Services
- Fitness Centers
- Veterinary Clinics

## 🔐 Authentication

The API uses Firebase Authentication:
1. Client authenticates with Firebase on frontend
2. Firebase ID token sent in Authorization header: `Bearer <token>`
3. Backend validates token with Firebase Admin SDK
4. User identified by Firebase UID

## 📱 Real-time Features

### WebSocket Chat
- Real-time messaging between clients and businesses
- Typing indicators
- Message read receipts
- File sharing support

### Push Notifications
- Appointment reminders (24h and 2h before)
- Booking confirmations
- Cancellation notifications
- New message alerts

## 🗃️ Database Schema

Key entities:
- **Business**: Business profiles with location and services
- **Client**: Client profiles with preferences
- **Appointment**: Booking records with status tracking
- **Service**: Business offerings with pricing
- **ChatRoom**: Communication channels
- **ChatMessage**: Individual messages
- **NotificationLog**: Notification tracking

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the [API documentation](http://localhost:8000/docs)
- Review the test cases for usage examples

---

**Built with ❤️ using FastAPI and modern Python practices**