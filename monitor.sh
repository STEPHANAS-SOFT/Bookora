#!/bin/bash
###############################################################################
# Bookora Backend - Automated Health Monitoring Script
#
# This script monitors the health of all Bookora services and sends alerts
# when issues are detected. It checks:
# - FastAPI application health
# - Database connectivity
# - Redis connectivity
# - Celery worker status
# - Disk space
# - Memory usage
# - CPU usage
# - Response times
#
# Usage:
#   ./monitor.sh [options]
#
# Options:
#   --interval SECONDS   Monitoring interval (default: 60)
#   --alert              Send alerts on failures
#   --once               Run once and exit
#   --verbose            Verbose output
#   --help               Show this help message
#
# Cron Setup (every 5 minutes):
#   */5 * * * * /path/to/monitor.sh --once --alert >> /path/to/logs/monitor.log 2>&1
#
# Author: Bookora Team
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="http://localhost:8000"
REDIS_HOST="localhost"
REDIS_PORT=6379
INTERVAL=60
RUN_ONCE=false
SEND_ALERTS=false
VERBOSE=false
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Thresholds
DISK_THRESHOLD=90  # Percent
MEMORY_THRESHOLD=90  # Percent
CPU_THRESHOLD=90  # Percent
RESPONSE_TIME_THRESHOLD=2000  # Milliseconds

# Status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║         🏥 HEALTH MONITORING SYSTEM 🏥                   ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    if [ "$VERBOSE" = true ]; then
        echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  $1${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
    fi
}

print_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}ℹ️  $1${NC}"
    fi
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

increment_check() {
    ((TOTAL_CHECKS++))
}

mark_passed() {
    ((PASSED_CHECKS++))
}

mark_failed() {
    ((FAILED_CHECKS++))
}

###############################################################################
# Parse Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --alert)
            SEND_ALERTS=true
            shift
            ;;
        --once)
            RUN_ONCE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: ./monitor.sh [options]"
            echo ""
            echo "Options:"
            echo "  --interval SECONDS   Monitoring interval (default: 60)"
            echo "  --alert              Send alerts on failures"
            echo "  --once               Run once and exit"
            echo "  --verbose            Verbose output"
            echo "  --help               Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

###############################################################################
# Health Check Functions
###############################################################################

check_api_health() {
    print_section "Checking API Health"
    increment_check
    
    local start_time=$(date +%s%3N)
    local response=$(curl -s -w "\n%{http_code}" "$API_URL/health" 2>/dev/null)
    local end_time=$(date +%s%3N)
    local response_time=$((end_time - start_time))
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        mark_passed
        print_success "API is healthy (${response_time}ms)"
        
        if [ $response_time -gt $RESPONSE_TIME_THRESHOLD ]; then
            print_warning "API response time is high: ${response_time}ms"
        fi
    else
        mark_failed
        print_error "API health check failed (HTTP $http_code)"
        return 1
    fi
}

check_database() {
    print_section "Checking Database Connectivity"
    increment_check
    
    # Load database config
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs 2>/dev/null)
    fi
    
    local db_host=${DATABASE_HOST:-localhost}
    local db_port=${DATABASE_PORT:-5432}
    local db_name=${DATABASE_NAME:-bookora}
    local db_user=${DATABASE_USER:-bookora_user}
    local db_pass=${DATABASE_PASSWORD}
    
    if [ -z "$db_pass" ]; then
        print_warning "Database password not configured"
        return 0
    fi
    
    export PGPASSWORD="$db_pass"
    
    if psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -c "SELECT 1;" &> /dev/null; then
        mark_passed
        print_success "Database is accessible"
        
        # Check database size
        local db_size=$(psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" \
            -t -c "SELECT pg_size_pretty(pg_database_size('$db_name'));" 2>/dev/null | xargs)
        
        if [ -n "$db_size" ]; then
            print_info "Database size: $db_size"
        fi
    else
        mark_failed
        print_error "Cannot connect to database"
        return 1
    fi
}

check_redis() {
    print_section "Checking Redis Connectivity"
    increment_check
    
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null; then
            mark_passed
            print_success "Redis is running"
            
            # Get Redis info
            local redis_version=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO server 2>/dev/null | grep "redis_version" | cut -d: -f2 | tr -d '\r')
            local redis_memory=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
            
            if [ -n "$redis_version" ]; then
                print_info "Redis version: $redis_version"
            fi
            if [ -n "$redis_memory" ]; then
                print_info "Redis memory: $redis_memory"
            fi
        else
            mark_failed
            print_error "Redis is not responding"
            return 1
        fi
    else
        print_warning "redis-cli not installed, skipping Redis check"
    fi
}

check_celery_worker() {
    print_section "Checking Celery Worker"
    increment_check
    
    # Check if Celery worker process is running
    if pgrep -f "celery.*worker" > /dev/null; then
        mark_passed
        print_success "Celery worker is running"
        
        # Try to inspect Celery
        if command -v celery &> /dev/null; then
            local worker_stats=$(celery -A app.core.celery_app inspect stats 2>/dev/null)
            if [ -n "$worker_stats" ]; then
                local active_workers=$(echo "$worker_stats" | grep -c "celery@" || echo "0")
                print_info "Active workers: $active_workers"
            fi
        fi
    else
        mark_failed
        print_error "Celery worker is not running"
        return 1
    fi
}

check_celery_beat() {
    print_section "Checking Celery Beat"
    increment_check
    
    if pgrep -f "celery.*beat" > /dev/null; then
        mark_passed
        print_success "Celery beat is running"
    else
        mark_failed
        print_error "Celery beat is not running"
        return 1
    fi
}

check_disk_space() {
    print_section "Checking Disk Space"
    increment_check
    
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -lt "$DISK_THRESHOLD" ]; then
        mark_passed
        print_success "Disk usage: ${disk_usage}%"
    else
        mark_failed
        print_error "Disk usage critical: ${disk_usage}%"
        return 1
    fi
}

check_memory_usage() {
    print_section "Checking Memory Usage"
    increment_check
    
    # macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local memory_pressure=$(memory_pressure 2>/dev/null | grep "System-wide memory free percentage" | awk '{print 100-$5}' | sed 's/%//')
        if [ -z "$memory_pressure" ]; then
            memory_pressure=0
        fi
    # Linux
    else
        local memory_pressure=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    fi
    
    if [ "$memory_pressure" -lt "$MEMORY_THRESHOLD" ]; then
        mark_passed
        print_success "Memory usage: ${memory_pressure}%"
    else
        print_warning "Memory usage high: ${memory_pressure}%"
        mark_passed
    fi
}

check_cpu_usage() {
    print_section "Checking CPU Usage"
    increment_check
    
    # macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local cpu_usage=$(ps -A -o %cpu | awk '{s+=$1} END {print int(s)}')
    # Linux
    else
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print int($2)}')
    fi
    
    if [ "$cpu_usage" -lt "$CPU_THRESHOLD" ]; then
        mark_passed
        print_success "CPU usage: ${cpu_usage}%"
    else
        print_warning "CPU usage high: ${cpu_usage}%"
        mark_passed
    fi
}

check_log_files() {
    print_section "Checking Log Files"
    increment_check
    
    local logs_dir="${SCRIPT_DIR}/logs"
    
    if [ -d "$logs_dir" ]; then
        # Check for recent errors in API log
        if [ -f "$logs_dir/api.log" ]; then
            local recent_errors=$(tail -n 100 "$logs_dir/api.log" | grep -ci "error" || echo "0")
            if [ "$recent_errors" -gt 10 ]; then
                print_warning "Found $recent_errors recent errors in API log"
            else
                mark_passed
                print_info "API log errors: $recent_errors"
            fi
        else
            mark_passed
            print_info "No API log file found"
        fi
    else
        mark_passed
        print_info "Logs directory not found"
    fi
}

check_api_endpoints() {
    print_section "Checking Critical API Endpoints"
    
    local endpoints=(
        "/api/v1/businesses"
        "/api/v1/clients"
        "/api/v1/appointments"
    )
    
    local api_key=${API_KEY:-bookora-dev-api-key-2025}
    
    for endpoint in "${endpoints[@]}"; do
        increment_check
        local url="${API_URL}${endpoint}"
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $api_key" "$url" 2>/dev/null)
        
        if [ "$http_code" = "200" ] || [ "$http_code" = "401" ]; then
            mark_passed
            print_info "Endpoint $endpoint: OK ($http_code)"
        else
            mark_failed
            print_error "Endpoint $endpoint: FAILED ($http_code)"
        fi
    done
}

###############################################################################
# Alert Functions
###############################################################################

send_alert() {
    if [ "$SEND_ALERTS" = false ]; then
        return
    fi
    
    print_section "Sending Alert"
    
    # Load email config
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs 2>/dev/null)
    fi
    
    if [ -z "$SMTP_USERNAME" ] || [ -z "$FROM_EMAIL" ]; then
        print_warning "Email not configured, skipping alert"
        return
    fi
    
    local subject="[ALERT] Bookora Health Check Failed - $TIMESTAMP"
    local body="Health monitoring detected issues with Bookora services.

Timestamp: $TIMESTAMP
Total Checks: $TOTAL_CHECKS
Passed: $PASSED_CHECKS
Failed: $FAILED_CHECKS
Warnings: $WARNINGS

Please check the system immediately.

This is an automated alert from Bookora Monitoring System."
    
    python3 - <<EOF
import smtplib
from email.mime.text import MIMEText
import os

smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
smtp_port = int(os.getenv('SMTP_PORT', '587'))
smtp_user = os.getenv('SMTP_USERNAME')
smtp_pass = os.getenv('SMTP_PASSWORD')
from_email = os.getenv('FROM_EMAIL')
to_email = os.getenv('ADMIN_EMAIL', from_email)

msg = MIMEText("""$body""")
msg['Subject'] = "$subject"
msg['From'] = from_email
msg['To'] = to_email

try:
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)
    server.quit()
    print("Alert sent successfully")
except Exception as e:
    print(f"Failed to send alert: {e}")
EOF
    
    print_info "Alert notification sent"
}

###############################################################################
# Summary Functions
###############################################################################

print_summary() {
    print_section "Health Check Summary"
    
    local health_percentage=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    
    echo -e "${CYAN}📊 Health Check Results${NC}"
    echo -e "   Timestamp: $TIMESTAMP"
    echo -e "   Total Checks: $TOTAL_CHECKS"
    echo -e "   Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "   Failed: ${RED}$FAILED_CHECKS${NC}"
    echo -e "   Warnings: ${YELLOW}$WARNINGS${NC}"
    echo -e "   Health: $health_percentage%"
    
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}✅ All systems operational${NC}"
        return 0
    else
        echo -e "${RED}❌ System issues detected${NC}"
        return 1
    fi
}

###############################################################################
# Main Execution
###############################################################################

run_health_checks() {
    # Reset counters
    TOTAL_CHECKS=0
    PASSED_CHECKS=0
    FAILED_CHECKS=0
    WARNINGS=0
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    
    print_banner
    echo -e "${CYAN}Starting health checks at $TIMESTAMP${NC}\n"
    
    # Run all checks
    check_api_health || true
    check_database || true
    check_redis || true
    check_celery_worker || true
    check_celery_beat || true
    check_disk_space || true
    check_memory_usage || true
    check_cpu_usage || true
    check_log_files || true
    check_api_endpoints || true
    
    # Print summary
    local exit_code=0
    if ! print_summary; then
        exit_code=1
        send_alert
    fi
    
    return $exit_code
}

main() {
    if [ "$RUN_ONCE" = true ]; then
        run_health_checks
        exit $?
    else
        echo -e "${CYAN}Starting continuous monitoring (interval: ${INTERVAL}s)${NC}"
        echo -e "${CYAN}Press Ctrl+C to stop${NC}\n"
        
        while true; do
            run_health_checks || true
            echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${CYAN}Next check in ${INTERVAL} seconds...${NC}\n"
            sleep "$INTERVAL"
        done
    fi
}

# Trap signals
trap 'echo -e "\n${YELLOW}⏸️  Monitoring stopped${NC}"; exit 0' INT TERM

# Run main
main

exit 0

