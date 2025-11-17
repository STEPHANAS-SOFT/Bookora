# 🚀 Bookora Automation - Quick Reference

This is a one-page quick reference for all automation commands in the Bookora backend.

## 📋 Essential Commands

### Start/Stop Services

```bash
# Start all services (development)
./start.sh

# Start all services (production)
./start.sh --prod

# Start with monitoring UI
./start.sh --prod --flower

# Stop all services
./stop.sh

# Force stop
./stop.sh --force
```

### Testing

```bash
# Run all tests
./test.sh

# Run with coverage
./test.sh --coverage

# Quick tests only
./test.sh --fast

# Specific test types
./test.sh --unit
./test.sh --integration
./test.sh --api
```

### Deployment

```bash
# Deploy to production
./deploy.sh --env production

# Deploy to staging
./deploy.sh --env staging

# Quick deploy (skip tests)
./deploy.sh --env staging --skip-tests --force

# Rollback deployment
./deploy.sh --rollback
```

### Database Backup

```bash
# Create backup
./backup.sh

# Backup with 30-day retention
./backup.sh --retention 30

# Backup with notification
./backup.sh --notify

# Restore backup
gunzip -c backups/bookora_*.sql.gz | psql -h localhost -U bookora_user -d bookora
```

### Health Monitoring

```bash
# One-time health check
./monitor.sh --once

# Continuous monitoring
./monitor.sh --interval 60 --alert

# Verbose check
./monitor.sh --once --verbose
```

### Cleanup

```bash
# Dry run (see what would be deleted)
./cleanup.sh --all --dry-run

# Clean everything
./cleanup.sh --all

# Clean specific items
./cleanup.sh --logs
./cleanup.sh --cache
./cleanup.sh --temp
```

### Environment Validation

```bash
# Validate .env configuration
python3 validate_env.py
```

## 🐳 Docker Commands

```bash
# Start all containers
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start production stack
docker-compose --profile production up -d

# View logs
docker-compose logs -f api
docker-compose logs -f celery_worker

# Stop containers
docker-compose down

# Rebuild containers
docker-compose up -d --build
```

## 🔄 Celery Commands

```bash
# Start worker
celery -A app.core.celery_app worker --loglevel=info

# Start beat scheduler
celery -A app.core.celery_app beat --loglevel=info

# Start Flower monitoring
celery -A app.core.celery_app flower --port=5555

# Check active tasks
celery -A app.core.celery_app inspect active

# Check scheduled tasks
celery -A app.core.celery_app inspect scheduled

# Check worker stats
celery -A app.core.celery_app inspect stats
```

## 📊 Management Commands

```bash
# Database migrations
python manage.py db:migrate
python manage.py db:seed
python manage.py db:reset

# Background tasks
python manage.py task:send-reminders
python manage.py task:cleanup
python manage.py task:stats

# Health checks
python manage.py health:check
python manage.py health:db

# Celery services
python manage.py celery:worker
python manage.py celery:beat
python manage.py celery:flower
```

## 💾 Database Commands

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current version
alembic current

# Connect to database
psql -h localhost -U bookora_user -d bookora

# Check database status
pg_isready -h localhost -p 5432
```

## 📝 Log Commands

```bash
# View API logs
tail -f logs/api.log

# View Celery worker logs
tail -f logs/celery_worker.log

# View all logs
tail -f logs/*.log

# Search logs for errors
grep -i error logs/api.log

# Last 100 lines
tail -n 100 logs/api.log
```

## 🔍 Debugging Commands

```bash
# Check running processes
ps aux | grep uvicorn
ps aux | grep celery
ps aux | grep redis

# Check port usage
lsof -i :8000  # API
lsof -i :6379  # Redis
lsof -i :5432  # PostgreSQL

# Check disk space
df -h

# Check memory usage
free -h  # Linux
memory_pressure  # macOS

# Test API endpoint
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

## 🌐 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | API Key required |
| API Docs | http://localhost:8000/docs | - |
| Flower | http://localhost:5555 | - |
| pgAdmin | http://localhost:8080 | admin@bookora.com / admin123 |
| Redis | redis://localhost:6379 | - |
| PostgreSQL | postgresql://localhost:5432 | bookora_user / bookora_password |

## 📅 Recommended Cron Jobs

Add to crontab (`crontab -e`):

```bash
# Backup - Daily at 2 AM
0 2 * * * cd /path/to/Bookora && ./backup.sh >> /path/to/logs/backup.log 2>&1

# Health Check - Every 5 minutes
*/5 * * * * cd /path/to/Bookora && ./monitor.sh --once --alert >> /path/to/logs/monitor.log 2>&1

# Cleanup - Weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/Bookora && ./cleanup.sh --all --force >> /path/to/logs/cleanup.log 2>&1
```

## ⚡ Performance Commands

```bash
# Check API performance
ab -n 1000 -c 10 http://localhost:8000/health

# Database performance
psql -h localhost -U bookora_user -d bookora -c "SELECT * FROM pg_stat_activity;"

# Redis performance
redis-cli --latency

# Check slow queries
psql -h localhost -U bookora_user -d bookora -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## 🛡️ Security Commands

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Check for security vulnerabilities
pip-audit

# Check environment security
python3 validate_env.py

# Generate new secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🔧 Troubleshooting Quick Fixes

```bash
# Services won't start
./stop.sh --force
./start.sh --prod

# Celery not processing tasks
pkill -f celery
./start.sh --prod

# Database connection issues
sudo systemctl restart postgresql  # Linux
brew services restart postgresql  # macOS

# Redis connection issues
redis-cli shutdown
redis-server --daemonize yes

# Clear cache
./cleanup.sh --cache --force

# Reset database (WARNING: deletes all data)
python manage.py db:reset
```

## 📊 Useful One-Liners

```bash
# Count total appointments
echo "SELECT COUNT(*) FROM appointments;" | psql -h localhost -U bookora_user -d bookora

# List all businesses
echo "SELECT id, name, email FROM businesses LIMIT 10;" | psql -h localhost -U bookora_user -d bookora

# Check Celery queue lengths
redis-cli llen celery

# Find large log files
find logs/ -type f -size +10M

# Disk usage of each directory
du -sh */ | sort -h

# Count lines of code
find app/ -name "*.py" | xargs wc -l

# Latest errors in logs
tail -100 logs/api.log | grep -i error

# API request count (from logs)
grep "GET\|POST\|PUT\|DELETE" logs/api.log | wc -l
```

## 🎯 Daily Workflow

### Morning
```bash
# Check system health
./monitor.sh --once --verbose

# Review logs
tail -100 logs/api.log
```

### Deployment
```bash
# Run tests
./test.sh --coverage

# Create backup
./backup.sh

# Deploy
./deploy.sh --env production

# Monitor
./monitor.sh --interval 30 --alert
```

### End of Day
```bash
# Review health
./monitor.sh --once

# Backup if needed
./backup.sh

# Optional cleanup
./cleanup.sh --logs --dry-run
```

## 📞 Emergency Procedures

### System Down
```bash
1. ./stop.sh --force
2. ./monitor.sh --once --verbose  # Check what's wrong
3. Check logs: tail -100 logs/api.log
4. ./start.sh --prod
5. ./monitor.sh --once --verbose  # Verify recovery
```

### Database Issues
```bash
1. ./backup.sh  # If possible
2. Check connection: psql -h localhost -U bookora_user -d bookora
3. Restart PostgreSQL
4. Restore from backup if needed
5. Run migrations: alembic upgrade head
```

### Deployment Rollback
```bash
1. ./deploy.sh --rollback
2. ./monitor.sh --once --verbose
3. Check logs for root cause
```

---

## 📚 Full Documentation

For detailed information, see:
- `AUTOMATION_README.md` - Complete automation guide
- `AUTOMATION_GUIDE.md` - Detailed task documentation
- `COMPLETE_API_DOCUMENTATION.md` - API reference

---

**Quick Help:**
- Any script: `./script.sh --help`
- Python management: `python manage.py --help`
- Validation: `python3 validate_env.py`

---

**Maintained by:** Bookora Team  
**Last Updated:** November 2024
