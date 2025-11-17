#!/bin/bash
###############################################################################
# Bookora Backend - Automated Startup Script
#
# This script automates the startup of all Bookora backend services:
# - PostgreSQL database (if using Docker)
# - Redis server (for Celery)
# - FastAPI application server
# - Celery worker (for background tasks)
# - Celery beat scheduler (for periodic tasks)
# - Celery Flower (optional monitoring UI)
#
# Usage:
#   ./start.sh [options]
#
# Options:
#   --dev         Development mode (default)
#   --prod        Production mode
#   --docker      Use Docker Compose
#   --no-celery   Skip Celery services
#   --flower      Start Flower monitoring UI
#   --help        Show this help message
#
# Author: Bookora Team
###############################################################################

set -e  # Exit on error

# Color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="Bookora Backend"
VENV_DIR="venv"
LOGS_DIR="logs"
PIDS_DIR=".pids"

# Default options
MODE="dev"
USE_DOCKER=false
NO_CELERY=false
START_FLOWER=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            MODE="dev"
            shift
            ;;
        --prod)
            MODE="prod"
            shift
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --no-celery)
            NO_CELERY=true
            shift
            ;;
        --flower)
            START_FLOWER=true
            shift
            ;;
        --help)
            echo "Usage: ./start.sh [options]"
            echo ""
            echo "Options:"
            echo "  --dev         Development mode (default)"
            echo "  --prod        Production mode"
            echo "  --docker      Use Docker Compose"
            echo "  --no-celery   Skip Celery services"
            echo "  --flower      Start Flower monitoring UI"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║                 🚀 BOOKORA BACKEND 🚀                    ║"
    echo "║                                                           ║"
    echo "║            Automated Service Startup Script              ║"
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

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

create_directories() {
    mkdir -p "$LOGS_DIR"
    mkdir -p "$PIDS_DIR"
    print_success "Created necessary directories"
}

###############################################################################
# Service Functions
###############################################################################

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    local missing_deps=()
    
    # Check Python
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python: $PYTHON_VERSION"
    else
        print_error "Python 3 not found"
        missing_deps+=("python3")
    fi
    
    # Check Redis (if not using Docker)
    if [ "$USE_DOCKER" = false ]; then
        if check_command redis-server; then
            print_success "Redis: Available"
        else
            print_warning "Redis not found - will try to use Docker"
            USE_DOCKER=true
        fi
    fi
    
    # Check Docker (if needed)
    if [ "$USE_DOCKER" = true ]; then
        if check_command docker; then
            print_success "Docker: Available"
        else
            print_error "Docker not found"
            missing_deps+=("docker")
        fi
        
        if check_command docker-compose; then
            print_success "Docker Compose: Available"
        else
            print_error "Docker Compose not found"
            missing_deps+=("docker-compose")
        fi
    fi
    
    # Check if .env exists
    if [ -f ".env" ]; then
        print_success ".env file found"
    else
        print_warning ".env file not found - will use defaults"
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

activate_venv() {
    print_section "Activating Virtual Environment"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_warning "Virtual environment not found. Creating..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi
    
    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment activated"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip --quiet
    
    # Install/update dependencies
    print_info "Installing/updating dependencies..."
    pip install -r requirements.txt --quiet
    print_success "Dependencies installed"
}

start_redis() {
    print_section "Starting Redis"
    
    if [ "$USE_DOCKER" = true ]; then
        print_info "Starting Redis with Docker..."
        docker-compose up -d redis
        sleep 2
        print_success "Redis started via Docker"
    else
        # Check if Redis is already running
        if redis-cli ping &> /dev/null; then
            print_success "Redis is already running"
        else
            print_info "Starting Redis server..."
            redis-server --daemonize yes --logfile "$LOGS_DIR/redis.log"
            sleep 2
            
            if redis-cli ping &> /dev/null; then
                print_success "Redis started successfully"
            else
                print_error "Failed to start Redis"
                exit 1
            fi
        fi
    fi
}

start_api() {
    print_section "Starting FastAPI Application"
    
    if [ "$MODE" = "prod" ]; then
        print_info "Starting in production mode..."
        nohup uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 4 \
            > "$LOGS_DIR/api.log" 2>&1 &
        echo $! > "$PIDS_DIR/api.pid"
    else
        print_info "Starting in development mode with auto-reload..."
        nohup uvicorn app.main:app \
            --reload \
            --host 0.0.0.0 \
            --port 8000 \
            > "$LOGS_DIR/api.log" 2>&1 &
        echo $! > "$PIDS_DIR/api.pid"
    fi
    
    sleep 3
    
    # Check if API is running
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "FastAPI started successfully on http://localhost:8000"
        print_info "API Docs: http://localhost:8000/docs"
    else
        print_error "Failed to start FastAPI"
        exit 1
    fi
}

start_celery_worker() {
    print_section "Starting Celery Worker"
    
    if [ "$MODE" = "prod" ]; then
        nohup celery -A app.core.celery_app worker \
            --loglevel=info \
            --concurrency=4 \
            > "$LOGS_DIR/celery_worker.log" 2>&1 &
        echo $! > "$PIDS_DIR/celery_worker.pid"
    else
        nohup celery -A app.core.celery_app worker \
            --loglevel=debug \
            --concurrency=2 \
            > "$LOGS_DIR/celery_worker.log" 2>&1 &
        echo $! > "$PIDS_DIR/celery_worker.pid"
    fi
    
    sleep 2
    print_success "Celery worker started"
}

start_celery_beat() {
    print_section "Starting Celery Beat Scheduler"
    
    nohup celery -A app.core.celery_app beat \
        --loglevel=info \
        > "$LOGS_DIR/celery_beat.log" 2>&1 &
    echo $! > "$PIDS_DIR/celery_beat.pid"
    
    sleep 2
    print_success "Celery beat scheduler started"
}

start_flower() {
    print_section "Starting Celery Flower"
    
    nohup celery -A app.core.celery_app flower \
        --port=5555 \
        > "$LOGS_DIR/flower.log" 2>&1 &
    echo $! > "$PIDS_DIR/flower.pid"
    
    sleep 2
    print_success "Flower monitoring UI started on http://localhost:5555"
}

run_migrations() {
    print_section "Running Database Migrations"
    
    print_info "Applying migrations..."
    alembic upgrade head
    print_success "Database migrations applied"
}

print_summary() {
    print_section "Startup Summary"
    
    echo -e "${GREEN}✅ All services started successfully!${NC}\n"
    
    echo -e "${CYAN}📋 Service Status:${NC}"
    echo -e "   • FastAPI:       ${GREEN}Running${NC} on http://localhost:8000"
    echo -e "   • API Docs:      ${GREEN}Available${NC} at http://localhost:8000/docs"
    echo -e "   • Redis:         ${GREEN}Running${NC}"
    
    if [ "$NO_CELERY" = false ]; then
        echo -e "   • Celery Worker: ${GREEN}Running${NC}"
        echo -e "   • Celery Beat:   ${GREEN}Running${NC}"
    fi
    
    if [ "$START_FLOWER" = true ]; then
        echo -e "   • Flower UI:     ${GREEN}Running${NC} on http://localhost:5555"
    fi
    
    echo -e "\n${CYAN}📂 Log Files:${NC}"
    echo -e "   • API:           $LOGS_DIR/api.log"
    
    if [ "$NO_CELERY" = false ]; then
        echo -e "   • Celery Worker: $LOGS_DIR/celery_worker.log"
        echo -e "   • Celery Beat:   $LOGS_DIR/celery_beat.log"
    fi
    
    if [ "$START_FLOWER" = true ]; then
        echo -e "   • Flower:        $LOGS_DIR/flower.log"
    fi
    
    echo -e "\n${CYAN}📌 Useful Commands:${NC}"
    echo -e "   • Stop all:      ${YELLOW}./stop.sh${NC}"
    echo -e "   • View logs:     ${YELLOW}tail -f $LOGS_DIR/api.log${NC}"
    echo -e "   • Health check:  ${YELLOW}curl http://localhost:8000/health${NC}"
    echo -e "   • Run tasks:     ${YELLOW}python manage.py task:send-reminders${NC}"
    
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}🎉 $PROJECT_NAME is now running in $MODE mode!${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_banner
    
    print_info "Starting in $MODE mode"
    if [ "$USE_DOCKER" = true ]; then
        print_info "Using Docker Compose"
    fi
    
    # Create necessary directories
    create_directories
    
    # Check prerequisites
    check_prerequisites
    
    # Activate virtual environment
    activate_venv
    
    # Start Redis
    start_redis
    
    # Run migrations
    run_migrations
    
    # Start FastAPI
    start_api
    
    # Start Celery services (unless disabled)
    if [ "$NO_CELERY" = false ]; then
        start_celery_worker
        start_celery_beat
    fi
    
    # Start Flower (if requested)
    if [ "$START_FLOWER" = true ]; then
        start_flower
    fi
    
    # Print summary
    print_summary
}

# Trap CTRL+C and cleanup
trap 'echo -e "\n${YELLOW}⏸️  Interrupted by user${NC}"; exit 130' INT

# Run main function
main

exit 0

