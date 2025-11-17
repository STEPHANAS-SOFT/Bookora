# ⚡ Quick Deployment Guide

**Complete step-by-step in 5 minutes!**

## 📋 Prerequisites
- SSH access to server
- Existing installation at `/root/Bookora`
- PostgreSQL and Redis running

---

## 🚀 Quick Steps

### 1️⃣ Connect & Backup (1 min)
```bash
ssh root@your-server-ip
cd /root
sudo systemctl stop bookora
cp -r Bookora Bookora_backup_$(date +%Y%m%d_%H%M%S)
```

### 2️⃣ Pull Latest Code (30 sec)
```bash
cd /root/Bookora
git pull origin main
```

### 3️⃣ Update Environment (1 min)
```bash
# If .env doesn't exist
cp env.template .env
nano .env  # Update values, then save (Ctrl+X, Y, Enter)
```

### 4️⃣ Update Dependencies (1 min)
```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
```

### 5️⃣ Update Services (1 min)
```bash
# Update main API service
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
[Install]
WantedBy=multi-user.target
EOF

# Create Celery worker service
sudo tee /etc/systemd/system/bookora-celery-worker.service <<'EOF'
[Unit]
Description=Bookora Celery Worker
After=network.target redis.service postgresql.service
[Service]
Type=simple
User=root
WorkingDirectory=/root/Bookora
Environment="PATH=/root/Bookora/venv/bin"
ExecStart=/root/Bookora/venv/bin/celery -A app.core.celery_app worker --loglevel=info --concurrency=4
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

# Create Celery beat service
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
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
```

### 6️⃣ Start Everything (30 sec)
```bash
sudo systemctl start bookora
sudo systemctl start bookora-celery-worker
sudo systemctl start bookora-celery-beat
sudo systemctl enable bookora bookora-celery-worker bookora-celery-beat
```

### 7️⃣ Verify (30 sec)
```bash
curl http://localhost:8500/health
sudo systemctl status bookora bookora-celery-worker bookora-celery-beat
```

---

## ✅ Done!

Your server is updated! 🎉

**Optional: Set up automation**
```bash
# Make scripts executable
chmod +x /root/Bookora/*.sh

# Add daily backup
(crontab -l 2>/dev/null; echo "0 2 * * * cd /root/Bookora && ./backup.sh >> logs/backup.log 2>&1") | crontab -
```

---

## 🆘 Troubleshooting

**Service won't start?**
```bash
sudo journalctl -u bookora -n 50
cd /root/Bookora && python3 validate_env.py
```

**Need to rollback?**
```bash
sudo systemctl stop bookora bookora-celery-worker bookora-celery-beat
cd /root
rm -rf Bookora
mv Bookora_backup_* Bookora
sudo systemctl start bookora
```

---

**Full guide:** See SERVER_DEPLOYMENT_GUIDE.md

