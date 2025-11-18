# 🚀 Update Server from Git - Step by Step Guide

This guide will walk you through updating your production server with the latest changes.

---

## 📋 Pre-Update Checklist

✅ All changes committed and pushed to GitHub  
✅ Local app tested and working  
✅ Database backup recommended (optional but safe)  

---

## 🔧 Step-by-Step Update Process

### Step 1: SSH into Your Server

```bash
ssh root@vmi2848672.contaboserver.net
# or
ssh root@wiseappsdev.cloud
```

---

### Step 2: Navigate to Project Directory

```bash
cd /root/Bookora
```

---

### Step 3: Check Current Status

```bash
# Check current branch and status
git status

# Check current commit
git log --oneline -1
```

---

### Step 4: Stash Any Local Changes (if needed)

If you see "Your local changes would be overwritten", stash them first:

```bash
# Stash local changes
git stash

# Or commit them if they're important
git add .
git commit -m "Local server changes before update"
```

---

### Step 5: Pull Latest Changes from GitHub

```bash
# Fetch latest changes
git fetch origin

# Pull and merge
git pull origin main
```

Expected output:
```
remote: Enumerating objects: ...
Unpacking objects: 100% ...
From https://github.com/STEPHANAS-SOFT/Bookora
 * branch            main       -> FETCH_HEAD
Updating 8bd9844..e2c17a2
Fast-forward
 app/main.py                | 22 +++++++---
 app/schemas/businesses.py  |  3 ++
 app/schemas/clients.py     |  3 ++
 3 files changed, 27 insertions(+), 14 deletions(-)
```

---

### Step 6: Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` prefix in your prompt.

---

### Step 7: Install Any New Dependencies (if needed)

```bash
pip install -r requirements.txt --upgrade
```

---

### Step 8: Create Database Migration for New Gallery Tables

```bash
# Set Python path
export PYTHONPATH=/root/Bookora

# Generate migration for new gallery tables
alembic revision --autogenerate -m "Add business and service gallery tables and image fields"

# Apply the migration
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade ... -> ..., Add gallery tables
```

---

### Step 9: Verify Database Changes

```bash
# Connect to PostgreSQL
psql -U stephen -d bookora_db

# List all tables
\dt

# You should see:
# - business_gallery
# - service_gallery

# Check business_gallery structure
\d business_gallery

# Check service_gallery structure
\d service_gallery

# Exit PostgreSQL
\q
```

---

### Step 10: Restart All Services

```bash
# Restart the API service
sudo systemctl restart bookora

# Restart Celery worker
sudo systemctl restart bookora-celery-worker

# Restart Celery beat
sudo systemctl restart bookora-celery-beat

# Wait a moment for services to start
sleep 5
```

---

### Step 11: Check Service Status

```bash
# Check all services
sudo systemctl status bookora bookora-celery-worker bookora-celery-beat

# Should show "active (running)" for all three
```

If any service fails, check logs:
```bash
# API logs
sudo journalctl -u bookora -n 50 --no-pager

# Celery worker logs
sudo journalctl -u bookora-celery-worker -n 50 --no-pager

# Celery beat logs
sudo journalctl -u bookora-celery-beat -n 50 --no-pager
```

---

### Step 12: Test the Updated API

```bash
# Test health endpoint
curl https://wiseappsdev.cloud/bookora/health

# Should return:
# {"status":"healthy","timestamp":...,"version":"1.0.0","environment":"production"}

# Test API docs (in your browser)
# Open: https://wiseappsdev.cloud/bookora/docs
```

---

### Step 13: Verify New Features

```bash
# Test that OpenAPI JSON loads
curl -s https://wiseappsdev.cloud/bookora/api/v1/openapi.json | jq '.info'

# Should show API title and version

# Check for new gallery endpoints
curl -s https://wiseappsdev.cloud/bookora/api/v1/openapi.json | jq '.paths | keys' | grep gallery
```

---

## ✅ What Was Updated

### 1. **Image Fields in Create/Update Schemas** ✨
   - `ClientCreate/ClientUpdate`: Now includes `profile_image_url` and `bio`
   - `BusinessCreate/BusinessUpdate`: Now includes `logo_url` and `cover_image_url`
   - `ServiceCreate/ServiceUpdate`: Already had `service_image_url`

### 2. **New Database Tables** 📊
   - `business_gallery` - For multiple business images
   - `service_gallery` - For multiple service images (before/after)

### 3. **New API Endpoints** 🌐
   - `POST /businesses/gallery/add` - Add business gallery image
   - `GET /businesses/gallery` - Get business gallery
   - `GET /businesses/gallery/my` - Get my business gallery
   - `PUT /businesses/gallery/{image_id}` - Update gallery image
   - `DELETE /businesses/gallery/{image_id}` - Delete gallery image
   - `POST /businesses/services/{service_id}/gallery/add` - Add service gallery image
   - `GET /businesses/services/{service_id}/gallery` - Get service gallery
   - `PUT /businesses/services/gallery/{image_id}` - Update service gallery image
   - `DELETE /businesses/services/gallery/{image_id}` - Delete service gallery image

### 4. **Environment Fix** 🔧
   - `main.py` now correctly uses `root_path="/bookora"` only in production
   - Config allows extra env variables (like `PGADMIN_*`)

---

## 🧪 Testing the New Features

### Test Client Registration with Profile Image:

```bash
curl -X POST "https://wiseappsdev.cloud/bookora/api/v1/clients/register?firebase_uid=test_uid_123" \
  -H "X-API-Key: bookora-dev-api-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_uid": "test_uid_123",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "profile_image_url": "https://example.com/profile.jpg"
  }'
```

### Test Business Registration with Logo and Cover:

```bash
curl -X POST "https://wiseappsdev.cloud/bookora/api/v1/businesses/register?firebase_uid=test_business_123" \
  -H "X-API-Key: bookora-dev-api-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_uid": "test_business_123",
    "owner_email": "owner@example.com",
    "name": "Test Salon",
    "category_id": "...",
    "logo_url": "https://example.com/logo.png",
    "cover_image_url": "https://example.com/cover.jpg"
  }'
```

---

## 🐛 Troubleshooting

### Issue: "Address already in use" error

```bash
# Find process using port 8500
sudo lsof -i :8500

# Kill the process if needed
sudo kill -9 <PID>

# Restart service
sudo systemctl restart bookora
```

### Issue: Migration fails

```bash
# Check migration status
alembic current

# Check migration history
alembic history

# If stuck, you can manually create the tables (last resort)
psql -U stephen -d bookora_db -f manual_migration.sql
```

### Issue: Services won't start

```bash
# Check detailed logs
sudo journalctl -u bookora -n 100 --no-pager

# Check if database is running
sudo systemctl status postgresql

# Check if Redis is running
sudo systemctl status redis
```

### Issue: Permission denied errors

```bash
# Fix ownership
sudo chown -R root:root /root/Bookora

# Fix executable permissions
chmod +x /root/Bookora/*.sh
```

---

## 📊 Post-Update Verification

After update, verify:

- ✅ Health endpoint responds: `https://wiseappsdev.cloud/bookora/health`
- ✅ API docs accessible: `https://wiseappsdev.cloud/bookora/docs`
- ✅ New image fields visible in Swagger UI
- ✅ Gallery endpoints appear in docs
- ✅ All services running: `systemctl status bookora*`
- ✅ No errors in logs: `journalctl -u bookora -n 50`

---

## 🔄 Rollback (if needed)

If something goes wrong, you can rollback:

```bash
# Rollback database migration
alembic downgrade -1

# Rollback git changes
git reset --hard <previous_commit_hash>

# Restart services
sudo systemctl restart bookora bookora-celery-worker bookora-celery-beat
```

---

## 📝 Summary of Commands (Quick Reference)

```bash
# 1. Navigate to project
cd /root/Bookora

# 2. Pull latest changes
git pull origin main

# 3. Activate virtual environment
source venv/bin/activate

# 4. Run migrations
export PYTHONPATH=/root/Bookora
alembic upgrade head

# 5. Restart services
sudo systemctl restart bookora bookora-celery-worker bookora-celery-beat

# 6. Check status
sudo systemctl status bookora

# 7. Test
curl https://wiseappsdev.cloud/bookora/health
```

---

## 🎉 Success!

Your server is now updated with:
- ✅ Complete image URL support in all registration/creation endpoints
- ✅ New gallery tables for unlimited images
- ✅ 10 new gallery management endpoints
- ✅ Production-ready configuration

The API is ready for FlutterFlow integration! 🚀

---

**Need Help?**

Check the logs:
- API: `sudo journalctl -u bookora -f`
- Celery: `sudo journalctl -u bookora-celery-worker -f`

Or refer to:
- `SERVER_DEPLOYMENT_GUIDE.md` - Complete deployment guide
- `IMAGE_HANDLING_GUIDE.md` - Image feature documentation
- `FLUTTERFLOW_INTEGRATION_GUIDE.md` - Frontend integration

