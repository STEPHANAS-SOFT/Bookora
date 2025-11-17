# 🚀 Bookora Server Deployment Guide

## Complete Step-by-Step Guide for Deploying to Your Linux Server

This guide will walk you through deploying the updated Bookora backend to your existing Linux server running on port 8500 with Nginx.

---

## 📋 Pre-Deployment Checklist

Before starting, make sure you have:
- ✅ SSH access to your Linux server
- ✅ Existing Bookora installation at `/root/Bookora`
- ✅ PostgreSQL running and accessible
- ✅ Redis installed and running
- ✅ Nginx configured for port 8500
- ✅ Root or sudo access

---

## 🔄 Step-by-Step Deployment Process

### Step 1: Connect to Your Server

```bash
# SSH into your server
ssh root@your-server-ip

# Or if using a different user with sudo
ssh your-username@your-server-ip
```

---

### Step 2: Stop the Current Running Service

```bash
# Stop the Bookora service
sudo systemctl stop bookora

# Verify it's stopped
sudo systemctl status bookora
```

**Expected output:** `inactive (dead)`

---

### Step 3: Backup Current Installation

```bash
# Create a backup of current installation
cd /root
sudo cp -r Bookora Bookora_backup_$(date +%Y%m%d_%H%M%S)

# Backup database (important!)
cd /root/Bookora
sudo -u postgres pg_dump bookora > /root/bookora_backup_$(date +%Y%m%d).sql

echo "✅ Backup completed"
```

---

### Step 4: Pull Latest Code from Git

```bash
# Navigate to Bookora directory
cd /root/Bookora

# Check current status
git status

# Fetch latest changes
git fetch origin

# Pull the latest code
git pull origin main

echo "✅ Code updated from Git"
```

**Expected output:**
```
Updating f586e5e..a691f4a
Fast-forward
 56 files changed, 17102 insertions(+), 1145 deletions(-)
 [... list of new files ...]
```

---

### Step 5: Update Environment Configuration

```bash
# Check if .env exists
cd /root/Bookora

if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp env.template .env
    echo "⚠️  Please edit .env with your actual values"
else
    echo "✅ .env already exists"
fi

# Edit .env with your actual configuration
nano .env

# Or use vim
# vim .env
```

**Required .env values to update:**

```bash
# Environment
ENVIRONMENT=production
DEBUG=False

# Security (IMPORTANT: Change these!)
SECRET_KEY=your-super-secret-key-change-this-in-production
API_KEY=your-production-api-key

# Database (Your existing values)
DATABASE_URL=postgresql://bookora_user:bookora_password@localhost:5432/bookora
DATABASE_USER=bookora_user
DATABASE_PASSWORD=your_actual_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=bookora

# Redis
REDIS_URL=redis://localhost:6379/0

# Firebase (for push notifications)
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour-Actual-Key\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id

# SMTP Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Bookora

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8500

# CORS (Add your domain)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Timezone
TIMEZONE=UTC
```

**Save and exit:** `Ctrl + X`, then `Y`, then `Enter`

---

### Step 6: Activate Virtual Environment and Update Dependencies

```bash
# Navigate to project directory
cd /root/Bookora

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install/update all dependencies
pip install -r requirements.txt

echo "✅ Dependencies updated"
```

**This will install new packages:**
- Celery (for background tasks)
- Redis client
- Flower (Celery monitoring)
- And all other new dependencies

---

### Step 7: Run Database Migrations

```bash
# Still in virtual environment
cd /root/Bookora

# Run Alembic migrations to update database schema
alembic upgrade head

echo "✅ Database migrations completed"
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ... -> ..., description
```

---

### Step 8: Update Systemd Service File

The new version has a better main.py structure. Update your service file:

```bash
# Create updated systemd service
sudo tee /etc/systemd/system/bookora.service <<'EOF'
[Unit]
Description=Bookora FastAPI Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/Bookora
Environment="PATH=/root/Bookora/venv/bin"
ExecStart=/root/Bookora/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8500 --workers 4
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

echo "✅ Systemd service updated"
```

**Key changes:**
- Uses `uvicorn` instead of direct `python main.py`
- Uses `app.main:app` (new structure)
- Runs with 4 workers for better performance
- Includes security hardening

---

### Step 9: Set Up Celery Services (NEW - for Background Tasks)

The new version includes background task automation. Set up Celery worker and beat scheduler:

#### 9.1. Create Celery Worker Service

```bash
sudo tee /etc/systemd/system/bookora-celery-worker.service <<'EOF'
[Unit]
Description=Bookora Celery Worker
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/Bookora
Environment="PATH=/root/Bookora/venv/bin"
ExecStart=/root/Bookora/venv/bin/celery -A app.core.celery_app worker --loglevel=info --concurrency=4 --queues=appointments,notifications,reviews,maintenance
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### 9.2. Create Celery Beat Service (Scheduler)

```bash
sudo tee /etc/systemd/system/bookora-celery-beat.service <<'EOF'
[Unit]
Description=Bookora Celery Beat Scheduler
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/Bookora
Environment="PATH=/root/Bookora/venv/bin"
ExecStart=/root/Bookora/venv/bin/celery -A app.core.celery_app beat --loglevel=info
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize new services
sudo systemctl daemon-reload

echo "✅ Celery services created"
```

---

### Step 10: Make Automation Scripts Executable

```bash
cd /root/Bookora

# Make all scripts executable
chmod +x start.sh stop.sh deploy.sh backup.sh monitor.sh cleanup.sh test.sh validate_env.py pre-push-test.sh

echo "✅ Scripts are now executable"
```

---

### Step 11: Validate Configuration

```bash
cd /root/Bookora
source venv/bin/activate

# Run environment validation
python3 validate_env.py
```

**Fix any errors shown before proceeding.**

---

### Step 12: Start All Services

```bash
# Start main API service
sudo systemctl start bookora

# Start Celery worker
sudo systemctl start bookora-celery-worker

# Start Celery beat scheduler
sudo systemctl start bookora-celery-beat

# Enable services to start on boot
sudo systemctl enable bookora
sudo systemctl enable bookora-celery-worker
sudo systemctl enable bookora-celery-beat

echo "✅ All services started"
```

---

### Step 13: Verify Services are Running

```bash
# Check API service
sudo systemctl status bookora

# Check Celery worker
sudo systemctl status bookora-celery-worker

# Check Celery beat
sudo systemctl status bookora-celery-beat

# Check if API is responding
curl http://localhost:8500/health

# Check API endpoints
curl http://localhost:8500/docs
```

**Expected health check response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-11-17T...",
  "version": "1.0.0"
}
```

---

### Step 14: Update Nginx Configuration (If Needed)

Check your existing Nginx config:

```bash
# View current Nginx configuration
cat /etc/nginx/sites-available/bookora
# or
cat /etc/nginx/conf.d/bookora.conf
```

**If you need to update it, here's a complete configuration:**

```bash
sudo nano /etc/nginx/sites-available/bookora
```

**Add or update:**

```nginx
upstream bookora_backend {
    server 127.0.0.1:8500;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS (if you have SSL)
    # return 301 https://$server_name$request_uri;

    # Or serve directly on HTTP
    location / {
        proxy_pass http://bookora_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for real-time chat)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (if any)
    location /static {
        alias /root/Bookora/static;
    }

    # API documentation
    location /docs {
        proxy_pass http://bookora_backend/docs;
        proxy_set_header Host $host;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://bookora_backend/health;
        access_log off;
    }
}

# HTTPS configuration (if you have SSL certificate)
# server {
#     listen 443 ssl http2;
#     server_name yourdomain.com www.yourdomain.com;
#
#     ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
#
#     # Same location blocks as above
#     location / {
#         proxy_pass http://bookora_backend;
#         # ... same proxy settings ...
#     }
# }
```

**Test and reload Nginx:**

```bash
# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx

echo "✅ Nginx updated"
```

---

### Step 15: Set Up Log Rotation

```bash
# Copy logrotate configuration
sudo cp /root/Bookora/logrotate.conf /etc/logrotate.d/bookora
sudo chmod 644 /etc/logrotate.d/bookora

# Test logrotate
sudo logrotate -f /etc/logrotate.d/bookora

echo "✅ Log rotation configured"
```

---

### Step 16: Set Up Automated Backups (Optional but Recommended)

```bash
# Add daily backup to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * cd /root/Bookora && ./backup.sh >> /root/Bookora/logs/backup.log 2>&1") | crontab -

# Add health monitoring (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /root/Bookora && ./monitor.sh --once --alert >> /root/Bookora/logs/monitor.log 2>&1") | crontab -

# Add weekly cleanup (Sundays at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * 0 cd /root/Bookora && ./cleanup.sh --all --force >> /root/Bookora/logs/cleanup.log 2>&1") | crontab -

# Verify crontab
crontab -l

echo "✅ Automated tasks scheduled"
```

---

### Step 17: Final Health Check

Run the comprehensive monitoring script:

```bash
cd /root/Bookora
./monitor.sh --once --verbose
```

**This will check:**
- ✅ API health endpoint
- ✅ Database connectivity
- ✅ Redis connectivity
- ✅ Celery worker status
- ✅ Celery beat status
- ✅ Disk space
- ✅ Memory usage
- ✅ CPU usage
- ✅ Log file errors
- ✅ Critical API endpoints

---

### Step 18: Test Key Features

```bash
# 1. Test health endpoint
curl http://localhost:8500/health

# 2. Test API documentation
curl http://localhost:8500/docs

# 3. Test business search (with API key)
curl -H "X-API-Key: your-api-key" \
     http://localhost:8500/api/v1/businesses/search?query=salon

# 4. Check Celery is processing tasks
sudo systemctl status bookora-celery-worker

# 5. Check logs
tail -f /root/Bookora/logs/api.log
```

---

## 🎯 Post-Deployment Checklist

After deployment, verify:

- [ ] ✅ API responds on port 8500
- [ ] ✅ Health endpoint returns healthy status
- [ ] ✅ Nginx proxy works correctly
- [ ] ✅ Database migrations applied successfully
- [ ] ✅ Celery worker is running
- [ ] ✅ Celery beat scheduler is running
- [ ] ✅ All services start on boot (enabled)
- [ ] ✅ Logs are being written correctly
- [ ] ✅ No errors in systemd logs
- [ ] ✅ Automated backups scheduled
- [ ] ✅ Health monitoring scheduled
- [ ] ✅ SSL certificate valid (if using HTTPS)

---

## 📊 Monitoring Commands

```bash
# View all Bookora services status
sudo systemctl status bookora bookora-celery-worker bookora-celery-beat

# View API logs (live)
tail -f /root/Bookora/logs/api.log

# View Celery worker logs
sudo journalctl -u bookora-celery-worker -f

# View Celery beat logs
sudo journalctl -u bookora-celery-beat -f

# View systemd logs for main API
sudo journalctl -u bookora -f

# Check disk usage
df -h

# Check memory usage
free -h

# Run health check
cd /root/Bookora && ./monitor.sh --once
```

---

## 🔧 Troubleshooting

### Issue: Service won't start

```bash
# Check systemd logs
sudo journalctl -u bookora -n 50

# Check Python errors
cd /root/Bookora
source venv/bin/activate
python3 -c "from app.main import app; print('OK')"

# Validate environment
python3 validate_env.py
```

### Issue: Database connection failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
psql -U bookora_user -d bookora -c "SELECT 1;"

# Check .env has correct credentials
cat /root/Bookora/.env | grep DATABASE
```

### Issue: Redis connection failed

```bash
# Check Redis is running
sudo systemctl status redis

# Test Redis connection
redis-cli ping

# Check Redis URL in .env
cat /root/Bookora/.env | grep REDIS
```

### Issue: Celery tasks not running

```bash
# Check Celery worker status
sudo systemctl status bookora-celery-worker

# Check Redis connection
redis-cli ping

# Restart Celery services
sudo systemctl restart bookora-celery-worker
sudo systemctl restart bookora-celery-beat
```

### Issue: Port 8500 already in use

```bash
# Check what's using port 8500
sudo lsof -i :8500

# Kill the process if needed
sudo kill -9 <PID>

# Or change port in .env
nano /root/Bookora/.env
# Change SERVER_PORT=8500 to different port
```

---

## 🔄 Rolling Back (If Something Goes Wrong)

```bash
# Stop all services
sudo systemctl stop bookora bookora-celery-worker bookora-celery-beat

# Restore from backup
cd /root
rm -rf Bookora
mv Bookora_backup_YYYYMMDD_HHMMSS Bookora

# Restore database
cd /root
sudo -u postgres psql bookora < bookora_backup_YYYYMMDD.sql

# Start services
sudo systemctl start bookora
```

---

## 📈 What's New in This Version

After deployment, you'll have:

1. **84 API Endpoints** - Complete REST API
2. **Background Task Automation** - Appointment reminders, review requests
3. **Real-time WebSocket** - For chat functionality
4. **Comprehensive Documentation** - 5,000+ lines
5. **Automation Scripts** - One-command operations
6. **Health Monitoring** - Automated checks
7. **Database Backups** - Automated daily backups
8. **Better Performance** - 4 workers, optimized queries
9. **Security Improvements** - Environment-based configuration
10. **FlutterFlow Integration** - Complete frontend guide

---

## 🚀 Using the New Automation Scripts

```bash
# Quick restart
cd /root/Bookora
./stop.sh
./start.sh --prod

# Create backup
./backup.sh

# Run health check
./monitor.sh --once

# Deploy updates in future
./deploy.sh --env production

# Clean up logs
./cleanup.sh --all
```

---

## 📞 Getting Help

If you encounter issues:

1. Check logs: `tail -f /root/Bookora/logs/api.log`
2. Run health check: `./monitor.sh --once --verbose`
3. Check systemd status: `sudo systemctl status bookora`
4. Validate environment: `python3 validate_env.py`

---

## ✅ Deployment Complete!

Your Bookora backend is now updated with:
- ✅ Latest code from Git
- ✅ All new features and endpoints
- ✅ Background task automation
- ✅ Improved performance and security
- ✅ Comprehensive monitoring
- ✅ Automated backups

**Your server is now running the production-ready version! 🎉**

---

**Repository:** https://github.com/STEPHANAS-SOFT/Bookora  
**Documentation:** See AUTOMATION_README.md and FLUTTERFLOW_INTEGRATION_GUIDE.md

