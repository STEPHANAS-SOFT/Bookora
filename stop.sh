#!/bin/bash
###############################################################################
# Bookora Backend - Automated Shutdown Script
#
# This script stops all running Bookora backend services gracefully.
#
# Usage:
#   ./stop.sh [options]
#
# Options:
#   --force       Force kill processes if graceful shutdown fails
#   --docker      Stop Docker containers
#   --help        Show this help message
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
NC='\033[0m'

# Configuration
PIDS_DIR=".pids"
FORCE=false
STOP_DOCKER=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --docker)
            STOP_DOCKER=true
            shift
            ;;
        --help)
            echo "Usage: ./stop.sh [options]"
            echo ""
            echo "Options:"
            echo "  --force       Force kill processes"
            echo "  --docker      Stop Docker containers"
            echo "  --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

stop_service() {
    local service_name=$1
    local pid_file="$PIDS_DIR/$service_name.pid"
    
    if [ ! -f "$pid_file" ]; then
        print_warning "$service_name: No PID file found (may not be running)"
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    
    # Check if process is running
    if ! ps -p "$pid" > /dev/null 2>&1; then
        print_warning "$service_name: Process not running (PID: $pid)"
        rm -f "$pid_file"
        return 0
    fi
    
    print_info "Stopping $service_name (PID: $pid)..."
    
    if [ "$FORCE" = true ]; then
        kill -9 "$pid" 2>/dev/null || true
    else
        kill "$pid" 2>/dev/null || true
        
        # Wait for graceful shutdown
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Graceful shutdown failed, forcing..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi
    
    rm -f "$pid_file"
    print_success "$service_name stopped"
}

main() {
    print_section "Stopping Bookora Backend Services"
    
    # Stop services in reverse order
    if [ -d "$PIDS_DIR" ]; then
        stop_service "flower"
        stop_service "celery_beat"
        stop_service "celery_worker"
        stop_service "api"
    else
        print_warning "No PID directory found"
    fi
    
    # Stop Celery processes by name (fallback)
    print_info "Checking for remaining Celery processes..."
    pkill -f "celery.*app.core.celery_app" 2>/dev/null || true
    
    # Stop Redis if requested
    if [ "$STOP_DOCKER" = false ]; then
        if pgrep redis-server > /dev/null; then
            read -p "$(echo -e ${YELLOW}'Stop Redis server? (y/N): '${NC})" -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_info "Stopping Redis..."
                redis-cli shutdown 2>/dev/null || true
                print_success "Redis stopped"
            fi
        fi
    fi
    
    # Stop Docker containers
    if [ "$STOP_DOCKER" = true ]; then
        print_info "Stopping Docker containers..."
        docker-compose down
        print_success "Docker containers stopped"
    fi
    
    # Clean up PID directory
    if [ -d "$PIDS_DIR" ] && [ -z "$(ls -A $PIDS_DIR)" ]; then
        rmdir "$PIDS_DIR"
    fi
    
    print_section "Shutdown Complete"
    echo -e "${GREEN}✅ All services stopped successfully${NC}\n"
}

main

exit 0

