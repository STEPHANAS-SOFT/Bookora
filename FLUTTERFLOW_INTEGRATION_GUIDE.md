# 📱 Bookora - FlutterFlow Integration Guide

## 🎯 Overview

This guide explains how to integrate your FlutterFlow frontend with the Bookora backend API, including endpoint calls, authentication, data flow, and automated processes that happen behind the scenes.

---

## 📋 Table of Contents

1. [API Configuration](#api-configuration)
2. [Authentication Setup](#authentication-setup)
3. [Making API Calls](#making-api-calls)
4. [Endpoint Reference](#endpoint-reference)
5. [Automation Workflows](#automation-workflows)
6. [Real-time Features](#real-time-features)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## 🔧 API Configuration

### Base URL Setup in FlutterFlow

1. **Go to**: Settings > API Calls > Add Group
2. **API Group Name**: `BookoraAPI`
3. **Base URL**: 
   - **Development**: `http://localhost:8000/api/v1`
   - **Production**: `https://your-domain.com/api/v1`

### Required Headers

All API calls must include these headers:

```json
{
  "X-API-Key": "your-api-key-here",
  "Content-Type": "application/json"
}
```

**Important**: Store your API key in FlutterFlow's App Constants:
- **Name**: `API_KEY`
- **Value**: `bookora-dev-api-key-2025` (or your production key)

---

## 🔐 Authentication Setup

### How Authentication Works

Bookora uses **Firebase UID-based authentication**:
1. User authenticates with Firebase on FlutterFlow
2. FlutterFlow gets Firebase UID
3. Every API call includes the Firebase UID
4. Backend validates and associates actions with the user

### Setting Up Authentication in FlutterFlow

#### Step 1: Configure Firebase Authentication

In FlutterFlow:
1. **Settings > Firebase** → Enable Authentication
2. Enable authentication methods (Email/Password, Google, etc.)
3. FlutterFlow automatically handles Firebase auth

#### Step 2: Store User Data

After successful Firebase authentication:

**Create App State Variables:**
- `firebaseUID` (String) - User's Firebase UID
- `userType` (String) - "client" or "business"
- `userProfile` (JSON) - User profile data

#### Step 3: Register/Login User in Bookora Backend

**For Clients:**

```
API Call: POST /clients
Headers:
  - X-API-Key: [Your API Key]
  - Content-Type: application/json

Body:
{
  "firebase_uid": "[Firebase UID from FlutterFlow Auth]",
  "first_name": "[User First Name]",
  "last_name": "[User Last Name]",
  "phone_number": "[Phone]",
  "profile_image_url": "[Optional Profile Image]",
  "fcm_token": "[FCM Token for Push Notifications]"
}
```

**For Businesses:**

```
API Call: POST /businesses
Headers:
  - X-API-Key: [Your API Key]
  - Content-Type: application/json

Body:
{
  "firebase_uid": "[Firebase UID]",
  "name": "[Business Name]",
  "description": "[Business Description]",
  "phone_number": "[Phone]",
  "email": "[Email]",
  "address": "[Address]",
  "latitude": [Latitude],
  "longitude": [Longitude],
  "category_id": "[Category UUID]",
  "logo_url": "[Optional Logo URL]",
  "fcm_token": "[FCM Token]"
}
```

---

## 📞 Making API Calls in FlutterFlow

### Creating API Calls

#### Example 1: Get Client Profile

**In FlutterFlow API Calls:**

1. **Name**: `GetClientProfile`
2. **Method**: `GET`
3. **URL**: `${baseURL}/clients/me`
4. **Headers**:
   ```json
   {
     "X-API-Key": "[App Constant: API_KEY]",
     "X-Firebase-UID": "[App State: firebaseUID]"
   }
   ```
5. **Response**: Parse JSON and store in App State variable `userProfile`

**What Happens on Backend:**
- ✅ API key is validated
- ✅ Firebase UID is verified
- ✅ Client record is retrieved from database
- ✅ Profile data is returned

**What Automation Happens:**
- None directly, but profile data is ready for use in appointments

---

#### Example 2: Search for Businesses

**In FlutterFlow API Calls:**

1. **Name**: `SearchBusinesses`
2. **Method**: `GET`
3. **URL**: `${baseURL}/businesses/search`
4. **Query Parameters**:
   - `query`: [Search text]
   - `category_id`: [Optional category filter]
   - `latitude`: [User's latitude]
   - `longitude`: [User's longitude]
   - `radius_km`: [Search radius, e.g., 10]
   - `min_rating`: [Optional, e.g., 4.0]
   - `skip`: [Pagination, default 0]
   - `limit`: [Results per page, default 20]
5. **Headers**:
   ```json
   {
     "X-API-Key": "[App Constant: API_KEY]"
   }
   ```

**What Happens on Backend:**
- ✅ API key is validated
- ✅ PostGIS calculates distances from user location
- ✅ Filters are applied (category, rating, radius)
- ✅ Results are sorted by distance or rating
- ✅ Paginated results are returned

**What Automation Happens:**
- None directly for search

**Response Format:**
```json
{
  "businesses": [
    {
      "id": "uuid",
      "name": "Elegant Hair Studio",
      "description": "Premium hair styling",
      "logo_url": "https://...",
      "average_rating": 4.5,
      "total_reviews": 120,
      "distance_km": 2.3,
      "category": {
        "id": "uuid",
        "name": "Hair Salon"
      },
      "address": "123 Main St"
    }
  ],
  "total": 50,
  "skip": 0,
  "limit": 20
}
```

---

#### Example 3: Book an Appointment

**In FlutterFlow API Calls:**

1. **Name**: `BookAppointment`
2. **Method**: `POST`
3. **URL**: `${baseURL}/appointments`
4. **Headers**:
   ```json
   {
     "X-API-Key": "[App Constant: API_KEY]",
     "X-Firebase-UID": "[App State: firebaseUID]"
   }
   ```
5. **Body**:
   ```json
   {
     "business_id": "[Selected Business UUID]",
     "service_id": "[Selected Service UUID]",
     "appointment_date": "2024-11-20T14:30:00Z",
     "notes": "Optional notes from client"
   }
   ```

**What Happens on Backend:**
1. ✅ API key validation
2. ✅ Firebase UID validation
3. ✅ Client record lookup
4. ✅ Business and service validation
5. ✅ Time slot availability check
6. ✅ Appointment creation with:
   - Unique confirmation code generation
   - Price calculation from service
   - Duration from service
   - Status set to PENDING
7. ✅ Database transaction committed

**What Automation Happens (IMMEDIATELY):**

🤖 **Automatic Confirmation Notification:**
- Push notification sent to client via FCM
- Notification logged in database
- Subject: "Appointment Confirmed"
- Body: Includes business name, date/time, confirmation code

**What Automation Happens (SCHEDULED):**

🤖 **24-Hour Reminder:**
- Celery task scheduled
- Will send push notification 24 hours before appointment
- Reminder includes: business name, date/time, confirmation code

🤖 **2-Hour Reminder:**
- Celery task scheduled
- Will send push notification 2 hours before appointment
- Final reminder before appointment

**Response Format:**
```json
{
  "id": "appointment-uuid",
  "confirmation_code": "BK-20241120-ABC123",
  "client_id": "client-uuid",
  "business_id": "business-uuid",
  "service_id": "service-uuid",
  "appointment_date": "2024-11-20T14:30:00Z",
  "duration_minutes": 60,
  "service_price": 75.00,
  "total_amount": 75.00,
  "status": "PENDING",
  "created_at": "2024-11-19T10:00:00Z"
}
```

---

#### Example 4: Add Business to Favorites

**In FlutterFlow API Calls:**

1. **Name**: `AddFavoriteBusiness`
2. **Method**: `POST`
3. **URL**: `${baseURL}/favorites`
4. **Headers**:
   ```json
   {
     "X-API-Key": "[App Constant: API_KEY]",
     "X-Firebase-UID": "[App State: firebaseUID]"
   }
   ```
5. **Body**:
   ```json
   {
     "business_id": "[Business UUID]"
   }
   ```

**What Happens on Backend:**
- ✅ Client identification via Firebase UID
- ✅ Business validation
- ✅ Duplicate check (prevents adding twice)
- ✅ Favorite record created

**What Automation Happens:**
- None directly, but favorite status affects search ranking

---

#### Example 5: Submit a Review

**In FlutterFlow API Calls:**

1. **Name**: `SubmitReview`
2. **Method**: `POST`
3. **URL**: `${baseURL}/reviews`
4. **Headers**:
   ```json
   {
     "X-API-Key": "[App Constant: API_KEY]",
     "X-Firebase-UID": "[App State: firebaseUID]"
   }
   ```
5. **Body**:
   ```json
   {
     "business_id": "[Business UUID]",
     "appointment_id": "[Appointment UUID]",
     "rating": 5,
     "review_text": "Great service! Highly recommend.",
     "service_quality": 5,
     "cleanliness": 5,
     "value_for_money": 4,
     "staff_professionalism": 5
   }
   ```

**What Happens on Backend:**
1. ✅ Client and appointment validation
2. ✅ Duplicate review check
3. ✅ Review creation
4. ✅ Database transaction

**What Automation Happens (IMMEDIATELY):**

🤖 **Review Statistics Update:**
- Celery task triggered: `aggregate_business_review_stats`
- Calculates new average rating for business
- Updates total review count
- Creates rating distribution (1-5 stars)
- Updates business profile with new stats

🤖 **Notification to Business Owner:**
- Push notification sent to business owner
- Subject: "New Review Received"
- Body: Rating and review preview

**Response Format:**
```json
{
  "id": "review-uuid",
  "client_id": "client-uuid",
  "business_id": "business-uuid",
  "appointment_id": "appointment-uuid",
  "rating": 5,
  "review_text": "Great service!",
  "is_verified": true,
  "created_at": "2024-11-19T15:00:00Z",
  "client": {
    "first_name": "John",
    "last_name": "D.",
    "profile_image_url": "https://..."
  }
}
```

---

#### Example 6: Send a Chat Message

**In FlutterFlow API Calls:**

1. **Name**: `SendChatMessage`
2. **Method**: `POST`
3. **URL**: `${baseURL}/communications/rooms/[room_id]/messages`
4. **Headers**:
   ```json
   {
     "X-API-Key": "[App Constant: API_KEY]",
     "X-Firebase-UID": "[App State: firebaseUID]"
   }
   ```
5. **Body**:
   ```json
   {
     "message": "What time are you available tomorrow?",
     "message_type": "text"
   }
   ```

**What Happens on Backend:**
1. ✅ Room access validation
2. ✅ Sender identification
3. ✅ Message creation
4. ✅ Recipient identification
5. ✅ Database commit

**What Automation Happens (IMMEDIATELY):**

🤖 **Real-time Message Delivery:**
- WebSocket notification sent to recipient (if online)
- Message appears instantly in their chat

🤖 **Push Notification (if recipient offline):**
- FCM push notification sent
- Subject: "New message from [Sender Name]"
- Body: Message preview

🤖 **Unread Count Update:**
- Chat room unread count incremented for recipient

---

## 📚 Complete Endpoint Reference

### 👤 Client Endpoints

#### 1. Register Client
```
POST /clients
Headers: X-API-Key
Body: { firebase_uid, first_name, last_name, phone_number, profile_image_url, fcm_token }
Returns: Client profile

Automation: None
```

#### 2. Get My Profile
```
GET /clients/me
Headers: X-API-Key, X-Firebase-UID
Returns: Client profile

Automation: None
```

#### 3. Update Profile
```
PUT /clients/me
Headers: X-API-Key, X-Firebase-UID
Body: { first_name, last_name, phone_number, profile_image_url }
Returns: Updated profile

Automation: None
```

#### 4. Get My Appointments
```
GET /clients/me/appointments
Headers: X-API-Key, X-Firebase-UID
Query: ?status=upcoming&skip=0&limit=20
Returns: List of appointments

Automation: None (but appointments have automated reminders)
```

---

### 🏢 Business Endpoints

#### 1. Register Business
```
POST /businesses
Headers: X-API-Key
Body: { firebase_uid, name, description, phone_number, email, address, latitude, longitude, category_id, logo_url, fcm_token }
Returns: Business profile

Automation: None initially
Note: Business needs admin approval (is_approved field)
```

#### 2. Search Businesses
```
GET /businesses/search
Headers: X-API-Key
Query: ?query=salon&latitude=40.7128&longitude=-74.0060&radius_km=10&category_id=uuid&min_rating=4
Returns: List of businesses with distance

Automation: None
```

#### 3. Get Business Details
```
GET /businesses/{business_id}
Headers: X-API-Key
Returns: Full business profile with services, hours, reviews

Automation: None
```

#### 4. Get My Business
```
GET /businesses/me
Headers: X-API-Key, X-Firebase-UID
Returns: Business owner's business profile

Automation: None
```

#### 5. Update Business
```
PUT /businesses/me
Headers: X-API-Key, X-Firebase-UID
Body: { name, description, phone_number, email, address, etc. }
Returns: Updated business profile

Automation: None
```

---

### 💇 Service Endpoints

#### 1. Get Business Services
```
GET /businesses/{business_id}/services
Headers: X-API-Key
Returns: List of services with prices and durations

Automation: None
```

#### 2. Create Service (Business Owner)
```
POST /businesses/me/services
Headers: X-API-Key, X-Firebase-UID
Body: { name, description, price, duration_minutes, service_image_url, requires_deposit, deposit_amount }
Returns: Created service

Automation: None
```

#### 3. Search Services Globally
```
GET /services/search
Headers: X-API-Key
Query: ?query=haircut&min_price=20&max_price=100&category_id=uuid&latitude=40.7128&longitude=-74.0060
Returns: Services from all businesses matching criteria

Automation: None
```

---

### 📅 Appointment Endpoints

#### 1. Book Appointment
```
POST /appointments
Headers: X-API-Key, X-Firebase-UID
Body: { business_id, service_id, appointment_date, notes }
Returns: Appointment with confirmation code

Automation:
✅ Immediate: Confirmation notification sent
✅ Scheduled: 24-hour reminder
✅ Scheduled: 2-hour reminder
```

#### 2. Get My Appointments (Client)
```
GET /appointments/me
Headers: X-API-Key, X-Firebase-UID
Query: ?status=upcoming&skip=0&limit=20
Returns: List of client's appointments

Automation: None
```

#### 3. Get Business Appointments (Business Owner)
```
GET /appointments/business
Headers: X-API-Key, X-Firebase-UID
Query: ?status=confirmed&date=2024-11-20
Returns: List of business's appointments

Automation: None
```

#### 4. Update Appointment Status
```
PUT /appointments/{appointment_id}/status
Headers: X-API-Key, X-Firebase-UID
Body: { status: "CONFIRMED" | "CANCELLED" | "COMPLETED" }
Returns: Updated appointment

Automation when status = CONFIRMED:
✅ Confirmation notification sent

Automation when status = COMPLETED:
✅ Next day at 10 AM: Review request sent to client
```

#### 5. Cancel Appointment
```
DELETE /appointments/{appointment_id}
Headers: X-API-Key, X-Firebase-UID
Returns: Success message

Automation:
✅ Cancellation notification sent to both parties
✅ Scheduled reminders are cancelled
```

---

### ⭐ Review Endpoints

#### 1. Submit Review
```
POST /reviews
Headers: X-API-Key, X-Firebase-UID
Body: { business_id, appointment_id, rating, review_text, service_quality, cleanliness, value_for_money, staff_professionalism }
Returns: Created review

Automation:
✅ Immediate: Business statistics updated (average rating, total reviews)
✅ Immediate: Business owner notified
```

#### 2. Get Business Reviews
```
GET /reviews/business/{business_id}
Headers: X-API-Key
Query: ?sort=recent&skip=0&limit=20
Returns: List of reviews with pagination

Automation: None
```

#### 3. Vote Review Helpful
```
POST /reviews/{review_id}/helpful
Headers: X-API-Key, X-Firebase-UID
Body: { is_helpful: true }
Returns: Updated helpfulness count

Automation: None
```

#### 4. Business Response to Review
```
POST /reviews/{review_id}/response
Headers: X-API-Key, X-Firebase-UID
Body: { response_text: "Thank you for your feedback!" }
Returns: Review with response

Automation:
✅ Notification sent to review author
```

---

### ❤️ Favorites Endpoints

#### 1. Add to Favorites
```
POST /favorites
Headers: X-API-Key, X-Firebase-UID
Body: { business_id }
Returns: Favorite record

Automation: None
```

#### 2. Get My Favorites
```
GET /favorites/me
Headers: X-API-Key, X-Firebase-UID
Returns: List of favorited businesses

Automation: None
```

#### 3. Remove from Favorites
```
DELETE /favorites/{business_id}
Headers: X-API-Key, X-Firebase-UID
Returns: Success message

Automation: None
```

#### 4. Create Collection
```
POST /favorites/collections
Headers: X-API-Key, X-Firebase-UID
Body: { name: "My Favorite Salons", description: "Best hair salons" }
Returns: Collection

Automation: None
```

#### 5. Add Business to Collection
```
POST /favorites/collections/{collection_id}/businesses
Headers: X-API-Key, X-Firebase-UID
Body: { business_id }
Returns: Success

Automation: None
```

---

### 💬 Chat/Communication Endpoints

#### 1. Get or Create Chat Room
```
POST /communications/rooms
Headers: X-API-Key, X-Firebase-UID
Body: { business_id }
Returns: Chat room (existing or new)

Automation: None
```

#### 2. Get My Chat Rooms
```
GET /communications/rooms/me
Headers: X-API-Key, X-Firebase-UID
Returns: List of chat rooms with last message

Automation: None
```

#### 3. Get Room Messages
```
GET /communications/rooms/{room_id}/messages
Headers: X-API-Key, X-Firebase-UID
Query: ?skip=0&limit=50
Returns: List of messages

Automation: None
```

#### 4. Send Message
```
POST /communications/rooms/{room_id}/messages
Headers: X-API-Key, X-Firebase-UID
Body: { message: "Hello!", message_type: "text" }
Returns: Created message

Automation:
✅ Immediate: Real-time WebSocket delivery (if recipient online)
✅ Immediate: Push notification (if recipient offline)
✅ Immediate: Unread count updated
```

#### 5. Mark Messages as Read
```
PUT /communications/rooms/{room_id}/read
Headers: X-API-Key, X-Firebase-UID
Returns: Success

Automation:
✅ Unread count reset to 0
```

---

### 🔔 Notification Endpoints

#### 1. Get My Notifications
```
GET /notifications/me
Headers: X-API-Key, X-Firebase-UID
Query: ?skip=0&limit=20&unread_only=true
Returns: List of notifications

Automation: None
```

#### 2. Mark Notification as Read
```
PUT /notifications/{notification_id}/read
Headers: X-API-Key, X-Firebase-UID
Returns: Updated notification

Automation: None
```

#### 3. Update Notification Preferences
```
PUT /notifications/preferences
Headers: X-API-Key, X-Firebase-UID
Body: { appointment_reminders: true, review_requests: false, promotions: true, chat_messages: true }
Returns: Updated preferences

Automation:
✅ Future notifications respect these preferences
```

---

### 👥 Staff Management Endpoints (Business Owner)

#### 1. Add Staff Member
```
POST /staff
Headers: X-API-Key, X-Firebase-UID
Body: { firebase_uid, first_name, last_name, role, phone_number, email, specialties }
Returns: Staff member record

Automation: None
```

#### 2. Get Business Staff
```
GET /staff/business/me
Headers: X-API-Key, X-Firebase-UID
Returns: List of staff members

Automation: None
```

#### 3. Set Staff Working Hours
```
POST /staff/{staff_id}/hours
Headers: X-API-Key, X-Firebase-UID
Body: { day_of_week: 1, start_time: "09:00:00", end_time: "17:00:00" }
Returns: Working hours record

Automation:
✅ Affects appointment availability calculations
```

#### 4. Add Staff Time Off
```
POST /staff/{staff_id}/time-off
Headers: X-API-Key, X-Firebase-UID
Body: { start_date: "2024-12-20", end_date: "2024-12-25", reason: "Holiday" }
Returns: Time off record

Automation:
✅ Affects appointment availability
✅ Existing appointments in this period may need rescheduling notification
```

---

### 🕐 Business Hours Endpoints

#### 1. Set Business Hours
```
POST /business-hours
Headers: X-API-Key, X-Firebase-UID
Body: { day_of_week: 1, open_time: "09:00:00", close_time: "18:00:00", is_closed: false }
Returns: Business hours record

Automation:
✅ Affects appointment availability
```

#### 2. Get Business Hours
```
GET /business-hours/business/{business_id}
Headers: X-API-Key
Returns: Weekly schedule

Automation: None
```

---

## 🤖 Complete Automation Workflows

### Workflow 1: Appointment Booking Journey

```
1. CLIENT ACTION: Books appointment via FlutterFlow
   ↓
2. API CALL: POST /appointments
   ↓
3. BACKEND PROCESSING:
   - Validates time slot
   - Creates appointment
   - Generates confirmation code
   ↓
4. IMMEDIATE AUTOMATION:
   ✅ Confirmation notification sent to client (push + in-app)
   ✅ Notification sent to business owner
   ✅ Notification logged in database
   ↓
5. SCHEDULED AUTOMATION:
   ✅ 24 hours before: Reminder sent to client
   ✅ 2 hours before: Final reminder sent to client
   ↓
6. APPOINTMENT DAY:
   - Client attends appointment
   - Business marks as COMPLETED
   ↓
7. NEXT DAY (10 AM):
   ✅ Review request sent to client
   ↓
8. CLIENT SUBMITS REVIEW:
   ✅ Business statistics updated immediately
   ✅ Business owner notified
```

---

### Workflow 2: Review and Rating Process

```
1. TRIGGER: Appointment marked as COMPLETED
   ↓
2. NEXT DAY AT 10 AM:
   ✅ Celery task: process_completed_appointments
   ✅ Checks if client already reviewed
   ✅ Sends review request notification
   ↓
3. CLIENT SUBMITS REVIEW (via FlutterFlow):
   API Call: POST /reviews
   ↓
4. IMMEDIATE AUTOMATION:
   ✅ Celery task: aggregate_business_review_stats
   ✅ Calculates:
      - New average rating
      - Total review count
      - Rating distribution (5-star, 4-star, etc.)
   ✅ Updates business profile
   ✅ Notifies business owner
   ↓
5. BUSINESS OWNER RESPONDS (optional):
   API Call: POST /reviews/{review_id}/response
   ↓
6. AUTOMATION:
   ✅ Notification sent to review author
```

---

### Workflow 3: Chat Message Flow

```
1. CLIENT SENDS MESSAGE (via FlutterFlow):
   API Call: POST /communications/rooms/{room_id}/messages
   ↓
2. BACKEND PROCESSING:
   - Saves message to database
   - Identifies recipient (business owner)
   ↓
3. IMMEDIATE AUTOMATION:
   ✅ Check if recipient is online (WebSocket connection)
   
   IF ONLINE:
   ✅ Real-time delivery via WebSocket
   ✅ Message appears instantly
   
   IF OFFLINE:
   ✅ FCM push notification sent
   ✅ Notification logged
   
   ALWAYS:
   ✅ Unread count incremented for recipient
   ↓
4. RECIPIENT OPENS CHAT:
   API Call: PUT /communications/rooms/{room_id}/read
   ↓
5. AUTOMATION:
   ✅ Unread count reset to 0
   ✅ All messages marked as read
```

---

### Workflow 4: Failed Notification Retry

```
1. NOTIFICATION FAILS (e.g., FCM token invalid):
   - Status set to FAILED
   - Retry count = 0
   ↓
2. EVERY HOUR:
   ✅ Celery task: retry_failed_notifications
   ✅ Finds failed notifications < 24 hours old
   ✅ Retry count < 3
   ↓
3. RETRY PROCESS:
   ✅ Attempts to resend notification
   ✅ If successful: Status → SENT
   ✅ If failed: Retry count++
   ↓
4. AFTER 3 FAILURES:
   - Notification marked as permanently failed
   - Admin notified for manual intervention
```

---

### Workflow 5: Daily Statistics Generation

```
1. EVERY DAY AT 1:00 AM:
   ✅ Celery task: generate_daily_statistics
   ↓
2. CALCULATES:
   - Total appointments (by status)
   - New user registrations
   - New business registrations
   - Review metrics (average rating, new reviews)
   - Revenue metrics
   - Popular services
   - Popular time slots
   ↓
3. STORES STATISTICS:
   - Saved to database
   - Available via admin dashboard
   ↓
4. NOTIFICATIONS:
   ✅ Daily report email to admin (optional)
```

---

### Workflow 6: Database Cleanup

```
1. WEEKLY (Monday 2:00 AM):
   ✅ Celery task: cleanup_old_notifications
   ✅ Deletes:
      - DELIVERED notifications > 90 days old
      - FAILED notifications > 30 days old
   ↓
2. DAILY (3:00 AM):
   ✅ Celery task: cleanup_expired_appointments
   ✅ Archives:
      - COMPLETED/CANCELLED appointments > 1 year old
      - Marks as inactive (preserves data)
   ↓
3. MONTHLY (1st of month, 4:00 AM):
   ✅ Celery task: cleanup_stale_chatrooms
   ✅ Archives:
      - Chat rooms with no activity in 6 months
      - Marks as inactive
```

---

## 🔄 Real-time Features (WebSocket)

### Setting Up WebSocket in FlutterFlow

#### Step 1: Install WebSocket Package

In FlutterFlow, add custom code dependency:
```yaml
dependencies:
  web_socket_channel: ^2.4.0
```

#### Step 2: WebSocket Connection

**WebSocket URL:**
- Development: `ws://localhost:8000/api/v1/ws/chat/{room_id}?token={firebase_uid}`
- Production: `wss://your-domain.com/api/v1/ws/chat/{room_id}?token={firebase_uid}`

#### Step 3: Custom WebSocket Widget

Create custom widget in FlutterFlow:

```dart
import 'package:web_socket_channel/web_socket_channel.dart';

class ChatWebSocket {
  WebSocketChannel? channel;
  
  void connect(String roomId, String firebaseUid) {
    final url = 'ws://localhost:8000/api/v1/ws/chat/$roomId?token=$firebaseUid';
    channel = WebSocketChannel.connect(Uri.parse(url));
    
    channel!.stream.listen((message) {
      // Parse incoming message
      final data = json.decode(message);
      
      // Update UI with new message
      // Add to message list
      // Scroll to bottom
    });
  }
  
  void sendMessage(String message) {
    if (channel != null) {
      channel!.sink.add(json.encode({
        'type': 'chat_message',
        'message': message
      }));
    }
  }
  
  void disconnect() {
    channel?.sink.close();
  }
}
```

### What Happens with WebSocket

**When Connected:**
1. Client connects to WebSocket with room_id and Firebase UID
2. Backend validates connection
3. Client is added to room's active connections

**When Message is Sent:**
1. Message sent via WebSocket
2. Backend receives and saves to database
3. Backend identifies all participants in room
4. Backend sends message to all connected participants instantly
5. Offline participants receive push notification

**When Disconnected:**
1. Connection closed
2. Client removed from active connections
3. Future messages will be delivered via push notification

---

## ❌ Error Handling

### Common HTTP Status Codes

| Code | Meaning | What to Do in FlutterFlow |
|------|---------|---------------------------|
| 200 | Success | Parse and display response |
| 201 | Created | Show success message |
| 400 | Bad Request | Show error message to user |
| 401 | Unauthorized | Check API key and Firebase UID |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Show field-specific errors |
| 500 | Server Error | Show generic error, retry later |

### Error Response Format

All errors return this structure:

```json
{
  "detail": "Error message here"
}
```

For validation errors (422):

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Invalid email format",
      "type": "value_error"
    }
  ]
}
```

### Handling Errors in FlutterFlow

1. **Add Error Handling to API Calls:**
   - Check response status code
   - Parse error detail
   - Show snackbar or dialog with error message

2. **Network Error Handling:**
   - Wrap API calls in try-catch
   - Show "No internet connection" message
   - Provide retry button

3. **Token Expiration:**
   - If 401 error, refresh Firebase token
   - Retry API call
   - If still fails, redirect to login

---

## 🎯 Best Practices

### 1. Authentication

✅ **DO:**
- Store Firebase UID in App State after authentication
- Include Firebase UID in X-Firebase-UID header for user-specific endpoints
- Store API key in App Constants, never hardcode
- Refresh FCM token and update backend when it changes

❌ **DON'T:**
- Hardcode API keys in custom code
- Store sensitive data in unsecured storage
- Make API calls without proper headers

### 2. Data Caching

✅ **DO:**
- Cache business listings for offline viewing
- Cache user profile locally
- Refresh cache periodically
- Show cached data while loading new data

❌ **DON'T:**
- Cache sensitive data like payment information
- Keep stale data indefinitely
- Cache data without expiration time

### 3. Loading States

✅ **DO:**
- Show loading indicators during API calls
- Disable buttons during submission
- Show skeleton screens for lists
- Handle slow network gracefully

### 4. Pagination

✅ **DO:**
- Use pagination for lists (businesses, appointments, messages)
- Implement infinite scroll or "Load More" button
- Start with skip=0, limit=20
- Increment skip by limit for next page

Example:
```
First page:  ?skip=0&limit=20
Second page: ?skip=20&limit=20
Third page:  ?skip=40&limit=20
```

### 5. Image Uploads

For profile images, business logos, and service images:

1. **Use Firebase Storage:**
   - Upload image to Firebase Storage in FlutterFlow
   - Get download URL
   - Send URL to backend API

2. **Image URL Format:**
   ```json
   {
     "profile_image_url": "https://firebasestorage.googleapis.com/..."
   }
   ```

### 6. Push Notifications

✅ **DO:**
- Request notification permission on app start
- Get FCM token after permission granted
- Send FCM token to backend during registration
- Update FCM token if it changes
- Handle notification taps (deep linking)

### 7. Location Services

✅ **DO:**
- Request location permission
- Get user's current location
- Send latitude/longitude with search requests
- Show distance from user location

### 8. Date/Time Handling

✅ **DO:**
- Always send dates in ISO 8601 format: `2024-11-20T14:30:00Z`
- Convert to user's timezone for display
- Use UTC for API calls
- Show timezone in appointment confirmations

---

## 📱 FlutterFlow Specific Tips

### 1. App State Variables

Create these App State variables:

```
- firebaseUID (String)
- userType (String) // "client" or "business"
- userProfile (JSON)
- apiKey (String)
- selectedBusinessId (String)
- selectedServiceId (String)
- cartItems (List<JSON>)
- unreadMessageCount (int)
- fcmToken (String)
```

### 2. Custom Actions

Create these custom actions:

- `registerUser()` - Register after Firebase auth
- `updateFCMToken()` - Update FCM token
- `handleNotificationTap()` - Navigate based on notification
- `formatDate()` - Format dates for display
- `calculateDistance()` - Calculate distance between coordinates

### 3. Page Navigation

```
Home → Business Search → Business Details → Book Appointment → Confirmation
                                         ↘ Chat with Business
                                         ↘ View Reviews
```

### 4. Bottom Navigation

Recommended tabs:
1. **Explore** - Search businesses
2. **Appointments** - User's appointments
3. **Messages** - Chat list
4. **Favorites** - Saved businesses
5. **Profile** - User settings

---

## 🎉 Summary

### Key Points to Remember:

1. **All API calls require X-API-Key header**
2. **User-specific calls require X-Firebase-UID header**
3. **Appointments trigger automatic reminders (24h and 2h)**
4. **Reviews trigger automatic statistics updates**
5. **Chat messages trigger real-time delivery or push notifications**
6. **Failed notifications are automatically retried hourly**
7. **Statistics are generated daily**
8. **Database cleanup happens automatically**
9. **WebSocket enables real-time chat**
10. **Always handle errors gracefully**

### Automation You Get for Free:

- ✅ Appointment confirmation notifications
- ✅ 24-hour appointment reminders
- ✅ 2-hour appointment reminders
- ✅ Review request after completed appointments
- ✅ Business statistics updates on new reviews
- ✅ Failed notification retries
- ✅ Real-time chat delivery
- ✅ Offline push notifications
- ✅ Daily statistics generation
- ✅ Database cleanup and maintenance

---

## 📞 Support

If you encounter issues:

1. Check API endpoint in FlutterFlow matches documentation
2. Verify headers are correctly set
3. Check response status code and error message
4. Review backend logs: `tail -f logs/api.log`
5. Test endpoint with Postman or curl
6. Check API documentation: http://localhost:8000/docs

---

**Your FlutterFlow app is now ready to integrate with the fully automated Bookora backend! 🚀**

