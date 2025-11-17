# Bookora Backend Automation Guide

## 📋 Overview

This guide explains all automated processes in the Bookora backend, including background tasks, scheduled jobs, and how to configure and manage them.

## 🔧 Architecture

The automation system is built on **Celery**, a distributed task queue system that runs background jobs asynchronously.

### Components:
- **Celery Worker**: Processes background tasks
- **Celery Beat**: Scheduler for periodic tasks
- **Redis**: Message broker and result backend
- **FastAPI**: Main application that can trigger tasks

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Redis Server

Redis is required for Celery to work.

```bash
# Using Docker
docker-compose up -d redis

# Or install locally on macOS
brew install redis
brew services start redis

# Or on Linux
sudo apt-get install redis-server
sudo systemctl start redis
```

### 3. Start Celery Worker

The worker processes background tasks as they're queued.

```bash
# Using the management script
python manage.py celery:worker

# Or directly
celery -A app.core.celery_app worker --loglevel=info
```

### 4. Start Celery Beat (Scheduler)

The beat scheduler triggers periodic tasks (reminders, cleanup, etc.).

```bash
# Using the management script
python manage.py celery:beat

# Or directly
celery -A app.core.celery_app beat --loglevel=info
```

### 5. (Optional) Start Flower Monitoring UI

Flower provides a web-based UI to monitor Celery tasks.

```bash
# Using the management script
python manage.py celery:flower

# Or directly
celery -A app.core.celery_app flower --port=5555
```

Then open http://localhost:5555 in your browser.

---

## 📅 Automated Tasks

### Appointment Tasks

#### 1. **Appointment Reminders**
- **File**: `app/tasks/appointment_tasks.py`
- **Task**: `check_and_send_reminders`
- **Schedule**: Every 5 minutes
- **Purpose**: Sends appointment reminders to clients

**What it does:**
- Sends 24-hour reminder (between 24-25 hours before appointment)
- Sends 2-hour reminder (between 2-2.5 hours before appointment)
- Only sends to CONFIRMED appointments
- Tracks which reminders have been sent to avoid duplicates
- Sends push notifications via FCM
- Logs all notification attempts

**Manual trigger:**
```bash
python manage.py task:send-reminders
```

#### 2. **Mark Missed Appointments**
- **Task**: `mark_missed_appointments`
- **Schedule**: Not scheduled by default (can be added)
- **Purpose**: Marks appointments as missed if client doesn't show up

**What it does:**
- Finds CONFIRMED appointments more than 1 hour past their time
- Changes status to CANCELLED
- Could be extended to charge no-show fees

#### 3. **Send Appointment Confirmation**
- **Task**: `send_appointment_confirmation`
- **Trigger**: Called when appointment is booked or confirmed
- **Purpose**: Sends confirmation notification to client

**Manual trigger from Python:**
```python
from app.tasks.appointment_tasks import send_appointment_confirmation
send_appointment_confirmation.delay(appointment_id, firebase_uid)
```

### Notification Tasks

#### 1. **Retry Failed Notifications**
- **File**: `app/tasks/notification_tasks.py`
- **Task**: `retry_failed_notifications`
- **Schedule**: Every hour
- **Purpose**: Retries sending notifications that previously failed

**What it does:**
- Finds notifications with FAILED status
- Checks if retry count is below max (default: 3)
- Only retries notifications less than 24 hours old
- Processes in batches of 100
- Updates retry count and status

#### 2. **Send Bulk Notifications**
- **Task**: `send_bulk_notification`
- **Trigger**: Manual or API call
- **Purpose**: Send notifications to multiple users at once

**Example usage:**
```python
from app.tasks.notification_tasks import send_bulk_notification

send_bulk_notification.delay(
    recipient_ids=["firebase_uid_1", "firebase_uid_2"],
    notification_type="push",
    event="announcement",
    subject="New Feature Available!",
    body="Check out our new feature...",
    data={"feature": "reviews"}
)
```

#### 3. **Send Single Notification**
- **Task**: `send_single_notification`
- **Trigger**: Manual or API call
- **Purpose**: Send a notification to one user

### Review Tasks

#### 1. **Process Completed Appointments**
- **File**: `app/tasks/review_tasks.py`
- **Task**: `process_completed_appointments`
- **Schedule**: Daily at 10:00 AM
- **Purpose**: Sends review requests for completed appointments

**What it does:**
- Finds appointments completed in last 24 hours
- Checks if client already reviewed the business
- Checks if review request already sent
- Sends push notification asking for review
- Logs notification attempt

#### 2. **Aggregate Business Review Stats**
- **Task**: `aggregate_business_review_stats`
- **Trigger**: Manual or after new review
- **Purpose**: Calculate and update business rating statistics

**What it does:**
- Calculates average rating
- Counts total reviews
- Creates rating distribution (1-5 stars)
- Updates business model with aggregated data

**Manual trigger:**
```python
from app.tasks.review_tasks import aggregate_business_review_stats
aggregate_business_review_stats.delay(business_id="uuid-here")
```

#### 3. **Send Review Reminder**
- **Task**: `send_review_reminder`
- **Trigger**: Manual (can be scheduled)
- **Purpose**: Reminds clients to leave reviews after 7 days

### Maintenance Tasks

#### 1. **Cleanup Old Notifications**
- **File**: `app/tasks/maintenance_tasks.py`
- **Task**: `cleanup_old_notifications`
- **Schedule**: Weekly on Monday at 2:00 AM
- **Purpose**: Remove old notification logs to save space

**What it does:**
- Deletes DELIVERED notifications older than 90 days
- Deletes FAILED notifications older than 30 days
- Helps maintain database performance

**Manual trigger:**
```bash
python manage.py task:cleanup
```

#### 2. **Cleanup Expired Appointments**
- **Task**: `cleanup_expired_appointments`
- **Schedule**: Daily at 3:00 AM
- **Purpose**: Archive old appointments

**What it does:**
- Finds appointments older than 1 year
- Only targets COMPLETED or CANCELLED appointments
- Marks them as inactive (doesn't delete)
- Preserves data for record-keeping

#### 3. **Cleanup Stale Chat Rooms**
- **Task**: `cleanup_stale_chatrooms`
- **Schedule**: Monthly on 1st at 4:00 AM
- **Purpose**: Archive inactive chat rooms

**What it does:**
- Finds chat rooms with no activity in 6 months
- Marks them as inactive
- Helps reduce clutter in active chat list

#### 4. **Generate Daily Statistics**
- **Task**: `generate_daily_statistics`
- **Schedule**: Daily at 1:00 AM
- **Purpose**: Calculate platform statistics

**What it does:**
- Counts appointments by status
- Tracks new user registrations
- Monitors business activity
- Calculates review metrics

**Manual trigger:**
```bash
python manage.py task:stats
```

#### 5. **Check Database Health**
- **Task**: `check_database_health`
- **Trigger**: Manual
- **Purpose**: Verify system health

**What it does:**
- Tests database connection
- Checks table sizes
- Identifies optimization opportunities

**Manual trigger:**
```bash
python manage.py health:check
```

#### 6. **Update Business Statistics**
- **Task**: `update_business_statistics`
- **Trigger**: Manual or scheduled
- **Purpose**: Update cached business metrics

**What it does:**
- Counts total appointments per business
- Calculates completion rates
- Updates average ratings
- Refreshes review counts

---

## 🎯 Task Queues

Tasks are organized into separate queues for better management:

| Queue | Purpose | Priority |
|-------|---------|----------|
| `appointments` | Appointment reminders and confirmations | High |
| `notifications` | Notification sending and retries | Medium |
| `reviews` | Review requests and aggregation | Medium |
| `maintenance` | Cleanup and statistics | Low |

### Running Specific Queues

```bash
# Only process appointment tasks
celery -A app.core.celery_app worker -Q appointments --loglevel=info

# Process multiple queues with priority
celery -A app.core.celery_app worker -Q appointments,notifications,reviews --loglevel=info
```

---

## 🔧 Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Timezone (for scheduled tasks)
TIMEZONE=UTC

# Firebase Cloud Messaging (for push notifications)
FCM_SERVER_KEY=your-fcm-server-key
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Customizing Task Schedules

Edit `app/core/celery_app.py` to modify the `beat_schedule`:

```python
celery_app.conf.beat_schedule = {
    "check-appointment-reminders": {
        "task": "app.tasks.appointment_tasks.check_and_send_reminders",
        "schedule": crontab(minute="*/5"),  # Change frequency here
        "options": {"queue": "appointments"},
    },
    # ... other tasks
}
```

**Crontab Schedule Examples:**
- `crontab(minute="*/15")` - Every 15 minutes
- `crontab(hour=8, minute=0)` - Daily at 8:00 AM
- `crontab(day_of_week=1, hour=9)` - Every Monday at 9:00 AM
- `crontab(day_of_month=1, hour=0)` - 1st of every month at midnight

---

## 🛠️ Management Commands

The `manage.py` script provides convenient commands for common operations.

### Database Commands

```bash
# Run migrations
python manage.py db:migrate

# Seed database with sample data
python manage.py db:seed

# Reset database (WARNING: Deletes all data)
python manage.py db:reset
```

### Task Commands

```bash
# Send appointment reminders manually
python manage.py task:send-reminders

# Run all cleanup tasks
python manage.py task:cleanup

# Generate statistics report
python manage.py task:stats
```

### Health Check Commands

```bash
# Full system health check
python manage.py health:check

# Database health check
python manage.py health:db
```

### Celery Commands

```bash
# Start Celery worker
python manage.py celery:worker

# Start Celery beat scheduler
python manage.py celery:beat

# Start Flower monitoring UI
python manage.py celery:flower
```

---

## 🐳 Docker Deployment

### Using Docker Compose

The project includes a `docker-compose.yml` with all services configured.

```bash
# Start all services (Postgres, Redis, API, Celery Worker, Celery Beat)
docker-compose up -d

# View logs
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat

# Stop services
docker-compose down
```

### Production Configuration

For production, uncomment the Celery services in `docker-compose.yml`:

```yaml
services:
  # ... other services ...
  
  celery_worker:
    build: .
    container_name: bookora_celery_worker
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=4
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://bookora_user:bookora_password@postgres:5432/bookora
      REDIS_URL: redis://redis:6379/0
    restart: unless-stopped
  
  celery_beat:
    build: .
    container_name: bookora_celery_beat
    command: celery -A app.core.celery_app beat --loglevel=info
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://bookora_user:bookora_password@postgres:5432/bookora
      REDIS_URL: redis://redis:6379/0
    restart: unless-stopped
```

---

## 📊 Monitoring

### Flower Dashboard

Flower provides real-time monitoring of Celery tasks:

```bash
celery -A app.core.celery_app flower --port=5555
```

Visit http://localhost:5555 to see:
- Active tasks
- Task history
- Worker status
- Task execution times
- Success/failure rates

### Logs

Celery logs provide detailed information:

```bash
# View worker logs
celery -A app.core.celery_app worker --loglevel=debug

# View beat logs
celery -A app.core.celery_app beat --loglevel=debug
```

### Database Monitoring

Check notification logs to see automation activity:

```sql
-- Recent notifications sent
SELECT * FROM notification_logs 
ORDER BY created_at DESC 
LIMIT 100;

-- Failed notifications needing attention
SELECT * FROM notification_logs 
WHERE status = 'failed' AND retry_count < max_retries
ORDER BY created_at DESC;

-- Reminder statistics
SELECT 
    DATE(sent_at) as date,
    COUNT(*) as reminders_sent,
    event
FROM notification_logs
WHERE event IN ('appointment_reminder_24h', 'appointment_reminder_2h')
GROUP BY DATE(sent_at), event
ORDER BY date DESC;
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. **Celery Worker Not Starting**

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Check Redis connection
python -c "import redis; r = redis.Redis(); print(r.ping())"
```

#### 2. **Tasks Not Executing**

```bash
# Check if worker is registered
celery -A app.core.celery_app inspect active

# Check scheduled tasks
celery -A app.core.celery_app inspect scheduled

# Check task stats
celery -A app.core.celery_app inspect stats
```

#### 3. **Beat Not Scheduling Tasks**

```bash
# Remove beat schedule file and restart
rm celerybeat-schedule.db
celery -A app.core.celery_app beat --loglevel=debug
```

#### 4. **Notifications Not Sending**

- Verify FCM credentials are configured
- Check Firebase Admin SDK initialization
- Verify FCM tokens are valid
- Check notification logs for error messages

```python
# Test FCM service directly
from app.services.fcm_service import fcm_service, FCMMessage

message = FCMMessage(
    token="test-token-here",
    title="Test",
    body="Test notification"
)

# This will show any FCM errors
await fcm_service.send_notification(message)
```

---

## 🚦 Best Practices

### 1. **Task Idempotency**
- Tasks should be safe to run multiple times
- Check for existing records before creating
- Use database transactions

### 2. **Error Handling**
- Always use try-except blocks
- Implement retry logic for transient failures
- Log errors with context

### 3. **Performance**
- Process tasks in batches when possible
- Use database indexes for queries
- Limit result set sizes

### 4. **Monitoring**
- Set up alerts for failed tasks
- Monitor task execution times
- Track queue sizes

### 5. **Testing**
- Test tasks independently
- Use test fixtures for data
- Mock external services (FCM, email)

---

## 📚 Additional Resources

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [Flower Documentation](https://flower.readthedocs.io/)

---

## 🆘 Support

If you encounter issues with automation:

1. Check the logs: `celery -A app.core.celery_app worker --loglevel=debug`
2. Run health check: `python manage.py health:check`
3. Test tasks manually: `python manage.py task:send-reminders`
4. Review notification logs in database
5. Check Redis connection: `redis-cli ping`

---

## 📝 Summary

The Bookora backend automation system handles:
- ✅ Appointment reminders (24h, 2h before)
- ✅ Review request automation
- ✅ Failed notification retries
- ✅ Database cleanup and maintenance
- ✅ Statistics generation
- ✅ Business metrics aggregation

All automated processes run in the background without manual intervention, ensuring a smooth user experience and optimal system performance.

