#!/bin/bash
###############################################################################
# Bookora Backend - Automated Database Backup Script
#
# This script creates automated backups of the PostgreSQL database with:
# - Timestamped backup files
# - Automatic compression
# - Retention policy (keeps last N backups)
# - Error handling and logging
# - Email notifications (optional)
#
# Usage:
#   ./backup.sh [options]
#
# Options:
#   --retention DAYS    Number of days to keep backups (default: 7)
#   --compress          Compress backup files (default: enabled)
#   --output DIR        Output directory (default: ./backups)
#   --notify            Send email notification on completion
#   --help              Show this help message
#
# Cron Setup (daily backup at 2 AM):
#   0 2 * * * /path/to/backup.sh >> /path/to/logs/backup.log 2>&1
#
# Author: Bookora Team
###############################################################################

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups"
RETENTION_DAYS=7
COMPRESS=true
NOTIFY=false
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${SCRIPT_DIR}/logs/backup_${TIMESTAMP}.log"

# Database configuration (loaded from .env)
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs)
fi

DATABASE_HOST=${DATABASE_HOST:-localhost}
DATABASE_PORT=${DATABASE_PORT:-5432}
DATABASE_NAME=${DATABASE_NAME:-bookora}
DATABASE_USER=${DATABASE_USER:-bookora_user}
DATABASE_PASSWORD=${DATABASE_PASSWORD}

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║          💾 DATABASE BACKUP AUTOMATION 💾                ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}

###############################################################################
# Parse Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --compress)
            COMPRESS=true
            shift
            ;;
        --output)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --notify)
            NOTIFY=true
            shift
            ;;
        --help)
            echo "Usage: ./backup.sh [options]"
            echo ""
            echo "Options:"
            echo "  --retention DAYS    Keep backups for N days (default: 7)"
            echo "  --compress          Compress backup files"
            echo "  --output DIR        Backup directory (default: ./backups)"
            echo "  --notify            Send email notification"
            echo "  --help              Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

###############################################################################
# Main Backup Logic
###############################################################################

create_directories() {
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    print_success "Created backup directories"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check pg_dump
    if ! command -v pg_dump &> /dev/null; then
        print_error "pg_dump not found. Install PostgreSQL client tools."
        exit 1
    fi
    print_success "pg_dump found"
    
    # Check database credentials
    if [ -z "$DATABASE_PASSWORD" ]; then
        print_error "DATABASE_PASSWORD not set in .env"
        exit 1
    fi
    print_success "Database credentials configured"
    
    # Test database connection
    print_info "Testing database connection..."
    export PGPASSWORD="$DATABASE_PASSWORD"
    if psql -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c "SELECT 1;" &> /dev/null; then
        print_success "Database connection successful"
    else
        print_error "Cannot connect to database"
        exit 1
    fi
}

calculate_backup_size() {
    print_section "Calculating Database Size"
    
    export PGPASSWORD="$DATABASE_PASSWORD"
    DB_SIZE=$(psql -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" \
        -t -c "SELECT pg_size_pretty(pg_database_size('$DATABASE_NAME'));" | xargs)
    
    print_info "Database size: $DB_SIZE"
}

create_backup() {
    print_section "Creating Database Backup"
    
    local backup_file="${BACKUP_DIR}/${DATABASE_NAME}_${TIMESTAMP}.sql"
    
    print_info "Backing up database: $DATABASE_NAME"
    print_info "Backup file: $backup_file"
    
    # Export password for pg_dump
    export PGPASSWORD="$DATABASE_PASSWORD"
    
    # Create backup with progress
    if pg_dump -h "$DATABASE_HOST" \
               -p "$DATABASE_PORT" \
               -U "$DATABASE_USER" \
               -d "$DATABASE_NAME" \
               -F p \
               --verbose \
               -f "$backup_file" 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Database backup created"
    else
        print_error "Backup creation failed"
        exit 1
    fi
    
    # Get backup file size
    BACKUP_SIZE=$(du -h "$backup_file" | cut -f1)
    print_info "Backup file size: $BACKUP_SIZE"
    
    # Compress backup if requested
    if [ "$COMPRESS" = true ]; then
        print_info "Compressing backup..."
        gzip "$backup_file"
        backup_file="${backup_file}.gz"
        COMPRESSED_SIZE=$(du -h "$backup_file" | cut -f1)
        print_success "Backup compressed to $COMPRESSED_SIZE"
    fi
    
    # Calculate checksum
    print_info "Calculating checksum..."
    if command -v sha256sum &> /dev/null; then
        CHECKSUM=$(sha256sum "$backup_file" | cut -d' ' -f1)
    else
        CHECKSUM=$(shasum -a 256 "$backup_file" | cut -d' ' -f1)
    fi
    echo "$CHECKSUM  $(basename "$backup_file")" > "${backup_file}.sha256"
    print_success "Checksum created: ${CHECKSUM:0:16}..."
}

cleanup_old_backups() {
    print_section "Cleaning Up Old Backups"
    
    print_info "Retention policy: $RETENTION_DAYS days"
    
    # Find and delete old backups
    local deleted_count=0
    while IFS= read -r -d '' file; do
        rm -f "$file"
        rm -f "${file}.sha256"
        print_info "Deleted: $(basename "$file")"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql*" -type f -mtime "+$RETENTION_DAYS" -print0)
    
    if [ $deleted_count -eq 0 ]; then
        print_info "No old backups to delete"
    else
        print_success "Deleted $deleted_count old backup(s)"
    fi
    
    # Show remaining backups
    local remaining_count=$(find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql*" -type f | wc -l)
    print_info "Remaining backups: $remaining_count file(s)"
}

list_backups() {
    print_section "Available Backups"
    
    local backups=$(find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql*" -type f ! -name "*.sha256" | sort -r)
    
    if [ -z "$backups" ]; then
        print_warning "No backups found"
        return
    fi
    
    echo -e "${CYAN}Recent backups:${NC}"
    local count=0
    while IFS= read -r backup; do
        local size=$(du -h "$backup" | cut -f1)
        local date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$backup" 2>/dev/null || stat -c "%y" "$backup" | cut -d. -f1)
        echo "  • $(basename "$backup") - $size - $date"
        ((count++))
        if [ $count -ge 5 ]; then
            break
        fi
    done <<< "$backups"
}

send_notification() {
    if [ "$NOTIFY" = false ]; then
        return
    fi
    
    print_section "Sending Notification"
    
    # Check if email is configured
    if [ -z "$SMTP_USERNAME" ] || [ -z "$FROM_EMAIL" ]; then
        print_warning "Email not configured, skipping notification"
        return
    fi
    
    print_info "Sending email notification..."
    
    # Create email body
    local subject="[Bookora] Database Backup Completed - $TIMESTAMP"
    local body="Database backup completed successfully.

Database: $DATABASE_NAME
Timestamp: $TIMESTAMP
Database Size: $DB_SIZE
Backup Size: ${COMPRESSED_SIZE:-$BACKUP_SIZE}
Checksum: ${CHECKSUM:0:32}...
Location: $BACKUP_DIR

Retention: $RETENTION_DAYS days

This is an automated message from Bookora Backup System."
    
    # Send email (using Python for simplicity)
    python3 - <<EOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
smtp_port = int(os.getenv('SMTP_PORT', '587'))
smtp_user = os.getenv('SMTP_USERNAME')
smtp_pass = os.getenv('SMTP_PASSWORD')
from_email = os.getenv('FROM_EMAIL')
to_email = os.getenv('ADMIN_EMAIL', from_email)

msg = MIMEMultipart()
msg['From'] = from_email
msg['To'] = to_email
msg['Subject'] = "$subject"

msg.attach(MIMEText("""$body""", 'plain'))

try:
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)
    server.quit()
    print("Email sent successfully")
except Exception as e:
    print(f"Failed to send email: {e}")
    exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Notification sent"
    else
        print_warning "Failed to send notification"
    fi
}

print_summary() {
    print_section "Backup Summary"
    
    echo -e "${GREEN}✅ Backup completed successfully!${NC}\n"
    
    echo -e "${CYAN}📋 Summary:${NC}"
    echo -e "   • Database:     $DATABASE_NAME"
    echo -e "   • Timestamp:    $TIMESTAMP"
    echo -e "   • Size:         ${COMPRESSED_SIZE:-$BACKUP_SIZE}"
    echo -e "   • Location:     $BACKUP_DIR"
    echo -e "   • Retention:    $RETENTION_DAYS days"
    
    echo -e "\n${CYAN}📝 Log file: $LOG_FILE${NC}"
    
    echo -e "\n${CYAN}💡 To restore from backup:${NC}"
    echo -e "   gunzip -c backup_file.sql.gz | psql -h \$HOST -U \$USER -d \$DB"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_banner
    
    # Initialize
    create_directories
    
    # Run backup process
    check_prerequisites
    calculate_backup_size
    create_backup
    cleanup_old_backups
    list_backups
    send_notification
    
    # Print summary
    print_summary
}

# Error handler
error_handler() {
    print_error "Backup failed at line $1"
    exit 1
}

trap 'error_handler $LINENO' ERR
trap 'echo -e "\n${YELLOW}⏸️  Backup interrupted${NC}"; exit 130' INT

# Run main
main

exit 0

