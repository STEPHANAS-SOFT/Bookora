# 🤖 Bookora Backend - Complete Automation Guide

Welcome to the Bookora Backend automation system! This guide will help you understand and use all the automation tools available for managing, deploying, and maintaining your Bookora application.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Automation Scripts](#automation-scripts)
4. [Background Tasks (Celery)](#background-tasks-celery)
5. [Docker Automation](#docker-automation)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Database Management](#database-management)
9. [Scheduled Tasks](#scheduled-tasks)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The Bookora backend includes comprehensive automation for:

- **Service Management**: Start/stop all services with one command
- **Testing**: Automated test execution with coverage reports
- **Deployment**: Zero-downtime deployments with rollback capability
- **Backups**: Automated database backups with retention policies
- **Monitoring**: Health checks and performance monitoring
- **Cleanup**: Log rotation and temporary file cleanup
- **Background Tasks**: Automated reminders, notifications, and maintenance
- **CI/CD**: Automated testing and deployment via GitHub Actions

---

## ⚡ Quick Start

### Initial Setup

1. **Validate Environment Configuration**
   ```bash
   python3 validate_env.py
   ```

2. **Start All Services**
   ```bash
   ./start.sh
   ```

3. **Verify Services are Running**
   ```bash
   ./monitor.sh --once
   ```

That's it! Your Bookora backend is now running with all automation enabled.

---

## 🛠️ Automation Scripts

### 1. `start.sh` - Automated Service Startup

Starts all Bookora services in the correct order with health checks.

**Usage:**
```bash
./start.sh [options]
```

**Options:**
- `--dev` - Development mode (auto-reload enabled)
- `--prod` - Production mode (optimized workers)
- `--docker` - Use Docker Compose
- `--no-celery` - Skip Celery services
- `--flower` - Start Flower monitoring UI

**Examples:**
```bash
# Development with auto-reload
./start.sh --dev

# Production mode
./start.sh --prod

# With monitoring UI
./start.sh --prod --flower

# Using Docker
./start.sh --docker
```

**What it does:**
- ✅ Activates virtual environment
- ✅ Installs/updates dependencies
- ✅ Starts Redis (if needed)
- ✅ Runs database migrations
- ✅ Starts FastAPI server
- ✅ Starts Celery worker
- ✅ Starts Celery beat scheduler
- ✅ Optionally starts Flower UI
- ✅ Performs health checks

---

### 2. `stop.sh` - Graceful Service Shutdown

Stops all running services gracefully.

**Usage:**
```bash
./stop.sh [options]
```

**Options:**
- `--force` - Force kill if graceful shutdown fails
- `--docker` - Stop Docker containers

**Examples:**
```bash
# Graceful shutdown
./stop.sh

# Force shutdown
./stop.sh --force

# Stop Docker services
./stop.sh --docker
```

---

### 3. `test.sh` - Automated Testing

Runs automated tests with various options.

**Usage:**
```bash
./test.sh [options]
```

**Options:**
- `--unit` - Run only unit tests
- `--integration` - Run only integration tests
- `--api` - Run only API endpoint tests
- `--coverage` - Generate coverage report
- `--verbose` - Verbose output
- `--fast` - Skip slow tests

**Examples:**
```bash
# Run all tests with coverage
./test.sh --coverage

# Run only unit tests
./test.sh --unit --verbose

# Quick test run
./test.sh --fast
```

**Output:**
- Test results in terminal
- Coverage reports in `htmlcov/index.html`
- XML coverage for CI/CD integration

---

### 4. `deploy.sh` - Automated Deployment

Deploys the application with pre and post-deployment checks.

**Usage:**
```bash
./deploy.sh [options]
```

**Options:**
- `--env ENV` - Environment (staging|production)
- `--skip-backup` - Skip database backup
- `--skip-tests` - Skip pre-deployment tests
- `--force` - Skip confirmations
- `--rollback` - Rollback to previous version

**Examples:**
```bash
# Deploy to production with all checks
./deploy.sh --env production

# Quick deployment (skip tests)
./deploy.sh --env staging --skip-tests --force

# Rollback if something went wrong
./deploy.sh --rollback
```

**Deployment Flow:**
1. Pre-deployment validation
2. Database backup
3. Run tests
4. Stop services
5. Update dependencies
6. Run migrations
7. Start services
8. Health verification
9. Rollback on failure

---

### 5. `backup.sh` - Database Backup

Creates automated database backups with compression.

**Usage:**
```bash
./backup.sh [options]
```

**Options:**
- `--retention DAYS` - Keep backups for N days (default: 7)
- `--compress` - Compress backup files (default: enabled)
- `--output DIR` - Backup directory
- `--notify` - Send email notification

**Examples:**
```bash
# Standard backup
./backup.sh

# Backup with 30-day retention
./backup.sh --retention 30

# With email notification
./backup.sh --notify
```

**Backup Features:**
- ✅ Timestamped backup files
- ✅ Automatic compression
- ✅ SHA256 checksums
- ✅ Retention policy
- ✅ Email notifications
- ✅ Pre-backup validation

**Restore from Backup:**
```bash
gunzip -c backups/bookora_20240117_120000.sql.gz | psql -h localhost -U bookora_user -d bookora
```

---

### 6. `monitor.sh` - Health Monitoring

Monitors system health and sends alerts.

**Usage:**
```bash
./monitor.sh [options]
```

**Options:**
- `--interval SECONDS` - Monitoring interval (default: 60)
- `--alert` - Send alerts on failures
- `--once` - Run once and exit
- `--verbose` - Verbose output

**Examples:**
```bash
# One-time health check
./monitor.sh --once

# Continuous monitoring
./monitor.sh --interval 30 --alert

# Verbose health check
./monitor.sh --once --verbose
```

**What it Checks:**
- ✅ API health endpoint
- ✅ Database connectivity
- ✅ Redis connectivity
- ✅ Celery worker status
- ✅ Celery beat status
- ✅ Disk space usage
- ✅ Memory usage
- ✅ CPU usage
- ✅ Recent log errors
- ✅ Critical API endpoints

---

### 7. `cleanup.sh` - System Cleanup

Cleans old logs, cache, and temporary files.

**Usage:**
```bash
./cleanup.sh [options]
```

**Options:**
- `--logs` - Clean old log files
- `--cache` - Clean cache files
- `--temp` - Clean temporary files
- `--all` - Clean everything
- `--dry-run` - Show what would be deleted
- `--force` - Skip confirmations

**Examples:**
```bash
# Dry run to see what would be cleaned
./cleanup.sh --all --dry-run

# Clean everything
./cleanup.sh --all

# Clean only logs
./cleanup.sh --logs --force
```

---

### 8. `validate_env.py` - Environment Validation

Validates environment configuration before startup.

**Usage:**
```bash
python3 validate_env.py
```

**What it Validates:**
- ✅ .env file existence
- ✅ Required environment variables
- ✅ Security settings
- ✅ Database connectivity
- ✅ Redis connectivity
- ✅ Firebase configuration

---

## 🔄 Background Tasks (Celery)

Celery handles automated background tasks and scheduled jobs.

### Task Queues

| Queue | Purpose | Priority |
|-------|---------|----------|
| `appointments` | Appointment reminders and confirmations | High |
| `notifications` | Notification sending and retries | Medium |
| `reviews` | Review requests and aggregation | Medium |
| `maintenance` | Cleanup and statistics | Low |

### Scheduled Tasks

#### Appointment Reminders
- **Task**: `check_and_send_reminders`
- **Schedule**: Every 5 minutes
- **Purpose**: Sends 24h and 2h appointment reminders

#### Review Requests
- **Task**: `process_completed_appointments`
- **Schedule**: Daily at 10:00 AM
- **Purpose**: Sends review requests after completed appointments

#### Failed Notification Retries
- **Task**: `retry_failed_notifications`
- **Schedule**: Every hour
- **Purpose**: Retries sending failed notifications

#### Database Cleanup
- **Task**: `cleanup_old_notifications`
- **Schedule**: Weekly on Monday at 2:00 AM
- **Purpose**: Removes old notification logs

#### Statistics Generation
- **Task**: `generate_daily_statistics`
- **Schedule**: Daily at 1:00 AM
- **Purpose**: Calculates platform statistics

### Manual Task Execution

```bash
# Send appointment reminders manually
python manage.py task:send-reminders

# Run cleanup tasks
python manage.py task:cleanup

# Generate statistics
python manage.py task:stats

# Check system health
python manage.py health:check
```

### Celery Monitoring

**Flower UI** (optional):
```bash
# Start Flower
./start.sh --flower

# Access at: http://localhost:5555
```

**CLI Monitoring:**
```bash
# Check active tasks
celery -A app.core.celery_app inspect active

# Check scheduled tasks
celery -A app.core.celery_app inspect scheduled

# Check worker stats
celery -A app.core.celery_app inspect stats
```

---

## 🐳 Docker Automation

### Docker Compose Services

| Service | Port | Purpose |
|---------|------|---------|
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache and Celery broker |
| `pgadmin` | 8080 | Database management UI |
| `api` | 8000 | FastAPI application |
| `celery_worker` | - | Background task worker |
| `celery_beat` | - | Task scheduler |
| `flower` | 5555 | Celery monitoring (optional) |
| `nginx` | 80/443 | Reverse proxy (production) |

### Docker Commands

**Start all services:**
```bash
docker-compose up -d
```

**Start specific services:**
```bash
docker-compose up -d postgres redis
```

**Start with monitoring:**
```bash
docker-compose --profile monitoring up -d
```

**Start production stack:**
```bash
docker-compose --profile production up -d
```

**View logs:**
```bash
docker-compose logs -f api
docker-compose logs -f celery_worker
```

**Stop services:**
```bash
docker-compose down
```

**Rebuild after code changes:**
```bash
docker-compose up -d --build
```

---

## 🚀 CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline automatically:
1. **Code Quality Checks** - Flake8, Black, isort
2. **Security Scanning** - Bandit security analysis
3. **Unit Tests** - Pytest with coverage
4. **Integration Tests** - Database and API tests
5. **Build Docker Image** - Containerization
6. **Deploy to Staging** - Automatic on `staging` branch
7. **Deploy to Production** - Automatic on `main` branch

### Required GitHub Secrets

```bash
# Docker Hub
DOCKER_USERNAME
DOCKER_PASSWORD

# Staging Server
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY

# Production Server
PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY

# Email Notifications
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
ADMIN_EMAIL
FROM_EMAIL
```

### Triggering Deployments

**Staging:**
```bash
git checkout staging
git merge develop
git push origin staging
```

**Production:**
```bash
git checkout main
git merge staging
git push origin main
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic health check |
| `/api/v1/businesses` | Business endpoint check |
| `/api/v1/clients` | Client endpoint check |
| `/api/v1/appointments` | Appointment endpoint check |

### Monitoring Tools

**1. Automated Health Checks:**
```bash
# One-time check
./monitor.sh --once

# Continuous monitoring with alerts
./monitor.sh --interval 60 --alert
```

**2. Flower UI (Celery):**
- Access: http://localhost:5555
- Shows active tasks, worker status, execution times

**3. pgAdmin (Database):**
- Access: http://localhost:8080
- Credentials: admin@bookora.com / admin123

**4. Logs:**
```bash
# API logs
tail -f logs/api.log

# Celery worker logs
tail -f logs/celery_worker.log

# All logs
tail -f logs/*.log
```

---

## 💾 Database Management

### Migrations

**Create new migration:**
```bash
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback migration:**
```bash
alembic downgrade -1
```

**Check current version:**
```bash
alembic current
```

### Seeding Data

**Seed database with sample data:**
```bash
python manage.py db:seed
```

### Backups and Restore

**Create backup:**
```bash
./backup.sh
```

**Restore backup:**
```bash
gunzip -c backups/bookora_YYYYMMDD_HHMMSS.sql.gz | psql -h localhost -U bookora_user -d bookora
```

---

## ⏰ Scheduled Tasks

### Cron Setup

Add these to your crontab (`crontab -e`):

```bash
# Database backup - Daily at 2 AM
0 2 * * * cd /path/to/Bookora && ./backup.sh >> /path/to/logs/backup.log 2>&1

# Health monitoring - Every 5 minutes
*/5 * * * * cd /path/to/Bookora && ./monitor.sh --once --alert >> /path/to/logs/monitor.log 2>&1

# Cleanup - Weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/Bookora && ./cleanup.sh --all --force >> /path/to/logs/cleanup.log 2>&1

# Log rotation - Daily at 4 AM
0 4 * * * /usr/sbin/logrotate /etc/logrotate.d/bookora
```

### systemd Service (Production)

Create `/etc/systemd/system/bookora.service`:

```ini
[Unit]
Description=Bookora Backend API
After=network.target postgresql.service redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/bookora
ExecStart=/var/www/bookora/start.sh --prod
ExecStop=/var/www/bookora/stop.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable bookora
sudo systemctl start bookora
sudo systemctl status bookora
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Services Won't Start

**Check logs:**
```bash
tail -f logs/api.log
```

**Validate environment:**
```bash
python3 validate_env.py
```

**Check port availability:**
```bash
lsof -i :8000  # API port
lsof -i :6379  # Redis port
lsof -i :5432  # PostgreSQL port
```

#### 2. Celery Tasks Not Running

**Check worker status:**
```bash
celery -A app.core.celery_app inspect active
```

**Check Redis:**
```bash
redis-cli ping
```

**Restart Celery:**
```bash
pkill -f celery
./start.sh --prod
```

#### 3. Database Connection Issues

**Test connection:**
```bash
psql -h localhost -U bookora_user -d bookora
```

**Check PostgreSQL status:**
```bash
# Linux
sudo systemctl status postgresql

# macOS
brew services list
```

#### 4. High Memory/CPU Usage

**Check resource usage:**
```bash
./monitor.sh --once --verbose
```

**Restart services:**
```bash
./stop.sh
./start.sh --prod
```

#### 5. Deployment Failures

**Check deployment log:**
```bash
cat logs/deploy_*.log | tail -n 100
```

**Rollback:**
```bash
./deploy.sh --rollback
```

**Manual recovery:**
```bash
./stop.sh --force
git checkout <previous-commit>
./start.sh --prod
```

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Full Automation Guide**: `AUTOMATION_GUIDE.md`
- **Quick Reference**: `AUTOMATION_QUICKREF.md`
- **API Documentation**: `COMPLETE_API_DOCUMENTATION.md`
- **Backend Summary**: `BACKEND_IMPLEMENTATION_SUMMARY.md`

---

## 💡 Best Practices

1. **Always validate environment** before starting services
2. **Run tests** before deploying to production
3. **Create backups** before major changes
4. **Monitor logs** regularly for errors
5. **Set up cron jobs** for automated maintenance
6. **Use Docker** for consistent deployments
7. **Enable CI/CD** for automated testing
8. **Configure alerts** for critical failures
9. **Review security** settings regularly
10. **Document changes** in deployment logs

---

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review log files in `logs/` directory
3. Run health check: `./monitor.sh --once --verbose`
4. Check deployment logs: `cat logs/deploy_*.log`

---

## 🎉 Summary

You now have a fully automated Bookora backend with:

- ✅ **One-command startup** - `./start.sh`
- ✅ **Automated testing** - `./test.sh --coverage`
- ✅ **Zero-downtime deployments** - `./deploy.sh --env production`
- ✅ **Automated backups** - `./backup.sh`
- ✅ **Health monitoring** - `./monitor.sh --interval 60 --alert`
- ✅ **Automated cleanup** - `./cleanup.sh --all`
- ✅ **Background tasks** - Celery with scheduled jobs
- ✅ **CI/CD pipeline** - GitHub Actions
- ✅ **Docker support** - `docker-compose up -d`

**Happy automating! 🚀**

