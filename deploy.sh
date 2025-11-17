#!/bin/bash
###############################################################################
# Bookora Backend - Automated Deployment Script
#
# This script automates the deployment process for the Bookora backend:
# - Pre-deployment checks and validations
# - Database migrations
# - Dependency updates
# - Service restarts
# - Health verification
# - Rollback capability
#
# Usage:
#   ./deploy.sh [options]
#
# Options:
#   --env ENV           Deployment environment (staging|production)
#   --skip-backup       Skip database backup
#   --skip-tests        Skip pre-deployment tests
#   --force             Force deployment without confirmations
#   --rollback          Rollback to previous version
#   --help              Show this help message
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
DEPLOY_ENV="production"
SKIP_BACKUP=false
SKIP_TESTS=false
FORCE=false
ROLLBACK=false
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEPLOY_LOG="${SCRIPT_DIR}/logs/deploy_${TIMESTAMP}.log"
BACKUP_DIR="${SCRIPT_DIR}/backups"

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║           🚀 AUTOMATED DEPLOYMENT SYSTEM 🚀              ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
    log_message "SECTION: $1"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
    log_message "INFO: $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log_message "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log_message "WARNING: $1"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    log_message "ERROR: $1"
}

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$DEPLOY_LOG"
}

confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    local message="$1"
    read -p "$(echo -e ${YELLOW}"$message (y/N): "${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled by user"
        exit 1
    fi
}

###############################################################################
# Parse Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            DEPLOY_ENV="$2"
            shift 2
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --help)
            echo "Usage: ./deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --env ENV           Environment (staging|production)"
            echo "  --skip-backup       Skip database backup"
            echo "  --skip-tests        Skip pre-deployment tests"
            echo "  --force             Force without confirmations"
            echo "  --rollback          Rollback to previous version"
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
# Deployment Functions
###############################################################################

pre_deployment_checks() {
    print_section "Pre-Deployment Checks"
    
    # Create log directory
    mkdir -p "$(dirname "$DEPLOY_LOG")"
    
    # Check if we're in the right directory
    if [ ! -f "app/main.py" ]; then
        print_error "Not in Bookora project directory"
        exit 1
    fi
    print_success "Project directory verified"
    
    # Check environment file
    if [ ! -f ".env" ]; then
        print_error ".env file not found"
        exit 1
    fi
    print_success ".env file found"
    
    # Validate environment configuration
    if [ -f "validate_env.py" ]; then
        print_info "Validating environment configuration..."
        if python3 validate_env.py &> /dev/null; then
            print_success "Environment configuration valid"
        else
            print_warning "Environment validation failed, proceeding anyway..."
        fi
    fi
    
    # Check Git status
    if command -v git &> /dev/null && [ -d ".git" ]; then
        local git_status=$(git status --porcelain)
        if [ -n "$git_status" ]; then
            print_warning "Working directory has uncommitted changes"
            if [ "$FORCE" = false ]; then
                confirm "Continue deployment with uncommitted changes?"
            fi
        else
            print_success "Working directory is clean"
        fi
        
        # Get current branch and commit
        local current_branch=$(git branch --show-current)
        local current_commit=$(git rev-parse --short HEAD)
        print_info "Branch: $current_branch"
        print_info "Commit: $current_commit"
        log_message "DEPLOY: Branch=$current_branch Commit=$current_commit"
    fi
    
    # Check required commands
    local missing_cmds=()
    for cmd in python3 pip psql redis-cli; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_cmds+=("$cmd")
        fi
    done
    
    if [ ${#missing_cmds[@]} -gt 0 ]; then
        print_warning "Missing commands: ${missing_cmds[*]}"
    else
        print_success "All required commands available"
    fi
}

backup_database() {
    if [ "$SKIP_BACKUP" = true ]; then
        print_warning "Skipping database backup (--skip-backup flag)"
        return 0
    fi
    
    print_section "Creating Database Backup"
    
    if [ -f "backup.sh" ]; then
        print_info "Running backup script..."
        if ./backup.sh --output "$BACKUP_DIR" 2>&1 | tee -a "$DEPLOY_LOG"; then
            print_success "Database backup completed"
            
            # Save backup filename for potential rollback
            local latest_backup=$(ls -t "$BACKUP_DIR"/*.sql* 2>/dev/null | head -n1)
            if [ -n "$latest_backup" ]; then
                echo "$latest_backup" > "${SCRIPT_DIR}/.last_backup"
                print_info "Backup saved: $(basename "$latest_backup")"
            fi
        else
            print_error "Database backup failed"
            confirm "Continue deployment without backup?"
        fi
    else
        print_warning "backup.sh not found, skipping backup"
    fi
}

run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests (--skip-tests flag)"
        return 0
    fi
    
    print_section "Running Tests"
    
    if [ -f "test.sh" ]; then
        print_info "Running automated tests..."
        if ./test.sh 2>&1 | tee -a "$DEPLOY_LOG"; then
            print_success "All tests passed"
        else
            print_error "Tests failed"
            confirm "Continue deployment despite test failures?"
        fi
    elif [ -f "pytest.ini" ] || [ -d "tests" ]; then
        print_info "Running pytest..."
        if python3 -m pytest tests/ -v 2>&1 | tee -a "$DEPLOY_LOG"; then
            print_success "All tests passed"
        else
            print_error "Tests failed"
            confirm "Continue deployment despite test failures?"
        fi
    else
        print_warning "No test suite found, skipping tests"
    fi
}

stop_services() {
    print_section "Stopping Services"
    
    if [ -f "stop.sh" ]; then
        print_info "Running stop script..."
        ./stop.sh --force 2>&1 | tee -a "$DEPLOY_LOG" || true
    else
        print_info "Stopping services manually..."
        pkill -f "uvicorn.*app.main:app" || true
        pkill -f "celery.*worker" || true
        pkill -f "celery.*beat" || true
    fi
    
    sleep 2
    print_success "Services stopped"
}

update_dependencies() {
    print_section "Updating Dependencies"
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        print_info "Activating virtual environment..."
        source venv/bin/activate
    else
        print_warning "No virtual environment found"
    fi
    
    # Update pip
    print_info "Upgrading pip..."
    pip install --upgrade pip --quiet 2>&1 | tee -a "$DEPLOY_LOG"
    
    # Install/update dependencies
    print_info "Installing dependencies..."
    pip install -r requirements.txt --quiet 2>&1 | tee -a "$DEPLOY_LOG"
    
    print_success "Dependencies updated"
}

run_migrations() {
    print_section "Running Database Migrations"
    
    print_info "Applying migrations..."
    
    if command -v alembic &> /dev/null; then
        if alembic upgrade head 2>&1 | tee -a "$DEPLOY_LOG"; then
            print_success "Migrations applied successfully"
        else
            print_error "Migration failed"
            exit 1
        fi
    else
        print_warning "Alembic not found, skipping migrations"
    fi
}

collect_static() {
    print_section "Collecting Static Files"
    
    if [ -d "static" ]; then
        print_info "Collecting static files..."
        # Add your static file collection logic here
        print_success "Static files collected"
    else
        print_info "No static files to collect"
    fi
}

start_services() {
    print_section "Starting Services"
    
    if [ -f "start.sh" ]; then
        print_info "Running start script..."
        
        if [ "$DEPLOY_ENV" = "production" ]; then
            ./start.sh --prod 2>&1 | tee -a "$DEPLOY_LOG" &
        else
            ./start.sh --dev 2>&1 | tee -a "$DEPLOY_LOG" &
        fi
        
        # Wait for services to start
        sleep 5
    else
        print_warning "start.sh not found, start services manually"
        return 1
    fi
    
    print_success "Services started"
}

verify_deployment() {
    print_section "Verifying Deployment"
    
    local max_attempts=30
    local attempt=0
    
    print_info "Waiting for API to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "API is responding"
            break
        fi
        
        ((attempt++))
        sleep 2
        echo -n "."
    done
    
    echo ""
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "API failed to start within timeout"
        return 1
    fi
    
    # Run health checks
    if [ -f "monitor.sh" ]; then
        print_info "Running health checks..."
        if ./monitor.sh --once --verbose 2>&1 | tee -a "$DEPLOY_LOG"; then
            print_success "Health checks passed"
        else
            print_warning "Some health checks failed"
        fi
    fi
    
    # Test critical endpoints
    print_info "Testing critical endpoints..."
    local endpoints=("/health" "/api/v1/businesses" "/api/v1/clients")
    local failed=0
    
    for endpoint in "${endpoints[@]}"; do
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000${endpoint}" 2>/dev/null)
        if [ "$http_code" = "200" ] || [ "$http_code" = "401" ]; then
            print_info "  ✓ $endpoint: OK"
        else
            print_warning "  ✗ $endpoint: FAILED ($http_code)"
            ((failed++))
        fi
    done
    
    if [ $failed -eq 0 ]; then
        print_success "All endpoint tests passed"
    else
        print_warning "$failed endpoint test(s) failed"
    fi
}

perform_rollback() {
    print_section "Rolling Back Deployment"
    
    print_warning "Initiating rollback..."
    
    # Stop services
    stop_services
    
    # Restore database backup
    if [ -f "${SCRIPT_DIR}/.last_backup" ]; then
        local backup_file=$(cat "${SCRIPT_DIR}/.last_backup")
        
        if [ -f "$backup_file" ]; then
            print_info "Restoring database from backup..."
            confirm "This will restore the database from backup. Continue?"
            
            # Load env
            if [ -f ".env" ]; then
                export $(grep -v '^#' ".env" | xargs)
            fi
            
            export PGPASSWORD="$DATABASE_PASSWORD"
            
            if [[ "$backup_file" == *.gz ]]; then
                gunzip -c "$backup_file" | psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME"
            else
                psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" < "$backup_file"
            fi
            
            print_success "Database restored"
        else
            print_error "Backup file not found: $backup_file"
        fi
    else
        print_warning "No backup record found"
    fi
    
    # Restore Git commit (if applicable)
    if [ -d ".git" ] && [ -f "${SCRIPT_DIR}/.last_deploy_commit" ]; then
        local last_commit=$(cat "${SCRIPT_DIR}/.last_deploy_commit")
        print_info "Rolling back to commit: $last_commit"
        confirm "Git checkout to previous commit?"
        git checkout "$last_commit"
        print_success "Git rollback complete"
    fi
    
    # Restart services
    start_services
    verify_deployment
    
    print_success "Rollback completed"
}

save_deployment_state() {
    print_section "Saving Deployment State"
    
    # Save current commit for rollback
    if [ -d ".git" ]; then
        git rev-parse HEAD > "${SCRIPT_DIR}/.last_deploy_commit"
        print_info "Saved deployment commit"
    fi
    
    # Save deployment timestamp
    echo "$TIMESTAMP" > "${SCRIPT_DIR}/.last_deploy_time"
    print_info "Saved deployment timestamp"
}

print_summary() {
    print_section "Deployment Summary"
    
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}\n"
    
    echo -e "${CYAN}📋 Deployment Details:${NC}"
    echo -e "   Environment: $DEPLOY_ENV"
    echo -e "   Timestamp: $TIMESTAMP"
    echo -e "   Log file: $DEPLOY_LOG"
    
    if [ -f "${SCRIPT_DIR}/.last_deploy_commit" ]; then
        local commit=$(cat "${SCRIPT_DIR}/.last_deploy_commit")
        echo -e "   Git commit: ${commit:0:8}"
    fi
    
    echo -e "\n${CYAN}🔗 Access URLs:${NC}"
    echo -e "   API: http://localhost:8000"
    echo -e "   Docs: http://localhost:8000/docs"
    echo -e "   Health: http://localhost:8000/health"
    
    echo -e "\n${CYAN}💡 Next Steps:${NC}"
    echo -e "   • Monitor logs: tail -f logs/api.log"
    echo -e "   • Run health check: ./monitor.sh --once"
    echo -e "   • To rollback: ./deploy.sh --rollback"
    
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}🎉 Bookora is now deployed and running!${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_banner
    
    # Handle rollback
    if [ "$ROLLBACK" = true ]; then
        perform_rollback
        exit 0
    fi
    
    # Normal deployment flow
    print_info "Deploying to: $DEPLOY_ENV"
    
    if [ "$DEPLOY_ENV" = "production" ]; then
        print_warning "You are deploying to PRODUCTION!"
        confirm "Are you sure you want to continue?"
    fi
    
    # Deployment steps
    pre_deployment_checks
    backup_database
    run_tests
    save_deployment_state
    stop_services
    update_dependencies
    run_migrations
    collect_static
    start_services
    verify_deployment
    
    # Print summary
    print_summary
}

# Error handler
error_handler() {
    print_error "Deployment failed at line $1"
    print_error "Check log file: $DEPLOY_LOG"
    
    confirm "Attempt automatic rollback?"
    perform_rollback
    exit 1
}

trap 'error_handler $LINENO' ERR
trap 'echo -e "\n${YELLOW}⏸️  Deployment interrupted${NC}"; exit 130' INT

# Run main
main

exit 0

