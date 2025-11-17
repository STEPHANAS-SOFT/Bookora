#!/bin/bash
###############################################################################
# Bookora Backend - Pre-Push Testing Script
#
# This script runs comprehensive tests before pushing to git to ensure:
# - Code quality
# - All imports work
# - Configuration is valid
# - Critical functionality works
# - No syntax errors
# - Documentation is up to date
#
# Usage:
#   ./pre-push-test.sh
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
TEST_FAILED=false
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║           🧪 PRE-PUSH TESTING SUITE 🧪                   ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_test() {
    echo -e "${CYAN}→ Testing: $1${NC}"
    ((TOTAL_TESTS++))
}

print_success() {
    echo -e "${GREEN}  ✅ $1${NC}"
    ((PASSED_TESTS++))
}

print_failure() {
    echo -e "${RED}  ❌ $1${NC}"
    ((FAILED_TESTS++))
    TEST_FAILED=true
}

print_warning() {
    echo -e "${YELLOW}  ⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}  ℹ️  $1${NC}"
}

###############################################################################
# Test Functions
###############################################################################

test_python_syntax() {
    print_section "1. Python Syntax Validation"
    
    print_test "Checking Python syntax for all .py files"
    
    local syntax_errors=0
    while IFS= read -r file; do
        if ! python3 -m py_compile "$file" 2>/dev/null; then
            print_failure "Syntax error in: $file"
            ((syntax_errors++))
        fi
    done < <(find app/ -name "*.py" -type f)
    
    if [ $syntax_errors -eq 0 ]; then
        print_success "All Python files have valid syntax"
    else
        print_failure "Found $syntax_errors file(s) with syntax errors"
    fi
}

test_imports() {
    print_section "2. Import Validation"
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    print_test "Testing main application imports"
    if python3 -c "from app.main import app; print('✓ main.py imports OK')" 2>/dev/null; then
        print_success "Main application imports successfully"
    else
        print_failure "Failed to import main application"
        python3 -c "from app.main import app" 2>&1 | tail -5
    fi
    
    print_test "Testing core modules"
    if python3 -c "from app.core.database import Base; from app.core.config import settings; print('✓ core modules OK')" 2>/dev/null; then
        print_success "Core modules import successfully"
    else
        print_failure "Failed to import core modules"
    fi
    
    print_test "Testing all models"
    if python3 -c "from app.models import Base; print('✓ models OK')" 2>/dev/null; then
        print_success "All models import successfully"
    else
        print_failure "Failed to import models"
    fi
    
    print_test "Testing Celery configuration"
    if python3 -c "from app.core.celery_app import celery_app; print('✓ celery OK')" 2>/dev/null; then
        print_success "Celery configuration imports successfully"
    else
        print_warning "Celery import failed (may need Redis running)"
    fi
}

test_environment_config() {
    print_section "3. Environment Configuration"
    
    print_test "Checking for .env file"
    if [ -f ".env" ]; then
        print_success ".env file exists"
    else
        print_warning ".env file not found (using defaults)"
    fi
    
    print_test "Checking env.template exists"
    if [ -f "env.template" ]; then
        print_success "env.template exists"
    else
        print_failure "env.template is missing"
    fi
    
    print_test "Validating environment configuration"
    if [ -f "validate_env.py" ]; then
        if python3 validate_env.py > /dev/null 2>&1; then
            print_success "Environment configuration is valid"
        else
            print_warning "Environment validation has warnings (see details above)"
        fi
    else
        print_info "Skipping env validation (validate_env.py not found)"
    fi
}

test_required_files() {
    print_section "4. Required Files Check"
    
    local required_files=(
        "requirements.txt"
        "Dockerfile"
        "docker-compose.yml"
        "README.md"
        ".gitignore"
        "app/main.py"
        "app/core/config.py"
        "app/core/database.py"
        "manage.py"
    )
    
    for file in "${required_files[@]}"; do
        print_test "Checking $file"
        if [ -f "$file" ]; then
            print_success "$file exists"
        else
            print_failure "$file is missing"
        fi
    done
}

test_automation_scripts() {
    print_section "5. Automation Scripts Check"
    
    local scripts=(
        "start.sh"
        "stop.sh"
        "test.sh"
        "deploy.sh"
        "backup.sh"
        "monitor.sh"
        "cleanup.sh"
    )
    
    for script in "${scripts[@]}"; do
        print_test "Checking $script"
        if [ -f "$script" ]; then
            if [ -x "$script" ]; then
                print_success "$script exists and is executable"
            else
                print_warning "$script exists but is not executable"
                chmod +x "$script"
                print_info "Made $script executable"
            fi
        else
            print_failure "$script is missing"
        fi
    done
}

test_docker_config() {
    print_section "6. Docker Configuration"
    
    print_test "Validating docker-compose.yml syntax"
    if command -v docker-compose &> /dev/null; then
        if docker-compose config > /dev/null 2>&1; then
            print_success "docker-compose.yml is valid"
        else
            print_failure "docker-compose.yml has syntax errors"
            docker-compose config 2>&1 | tail -10
        fi
    else
        print_info "docker-compose not installed, skipping validation"
    fi
    
    print_test "Checking Dockerfile"
    if [ -f "Dockerfile" ]; then
        print_success "Dockerfile exists"
    else
        print_failure "Dockerfile is missing"
    fi
}

test_git_status() {
    print_section "7. Git Status Check"
    
    if ! command -v git &> /dev/null; then
        print_info "Git not installed, skipping git checks"
        return
    fi
    
    print_test "Checking for uncommitted changes"
    if git diff --quiet && git diff --cached --quiet; then
        print_success "No uncommitted changes"
    else
        print_warning "You have uncommitted changes"
        print_info "Files changed:"
        git status --short | head -10
    fi
    
    print_test "Checking current branch"
    local branch=$(git branch --show-current)
    print_info "Current branch: $branch"
    
    if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
        print_warning "You're on $branch branch"
        print_info "Consider pushing to develop or feature branch first"
    fi
}

test_documentation() {
    print_section "8. Documentation Check"
    
    local docs=(
        "README.md"
        "AUTOMATION_README.md"
        "AUTOMATION_QUICKREF.md"
        "AUTOMATION_SUMMARY.md"
        "FLUTTERFLOW_INTEGRATION_GUIDE.md"
        "COMPLETE_API_DOCUMENTATION.md"
    )
    
    for doc in "${docs[@]}"; do
        print_test "Checking $doc"
        if [ -f "$doc" ]; then
            # Check if file is not empty
            if [ -s "$doc" ]; then
                print_success "$doc exists and has content"
            else
                print_warning "$doc exists but is empty"
            fi
        else
            print_warning "$doc is missing"
        fi
    done
}

test_security() {
    print_section "9. Security Check"
    
    print_test "Checking for exposed secrets"
    
    # Check if .env is in gitignore
    if grep -q "^\.env$" .gitignore 2>/dev/null; then
        print_success ".env is in .gitignore"
    else
        print_failure ".env should be in .gitignore"
    fi
    
    # Check if .env would be committed
    if git ls-files --error-unmatch .env 2>/dev/null; then
        print_failure "WARNING: .env is tracked by git! Remove it immediately!"
        print_info "Run: git rm --cached .env"
    else
        print_success ".env is not tracked by git"
    fi
    
    # Check for hardcoded secrets in tracked files
    print_test "Scanning for potential hardcoded secrets"
    local secret_patterns=(
        "password.*=.*['\"]"
        "secret.*=.*['\"]"
        "api.*key.*=.*['\"]"
        "token.*=.*['\"]"
    )
    
    local found_secrets=0
    for pattern in "${secret_patterns[@]}"; do
        if git grep -i "$pattern" -- '*.py' '*.yml' '*.yaml' 2>/dev/null | grep -v "template" | grep -v "example" | grep -q .; then
            ((found_secrets++))
        fi
    done
    
    if [ $found_secrets -eq 0 ]; then
        print_success "No obvious hardcoded secrets found"
    else
        print_warning "Found $found_secrets potential hardcoded secret(s)"
        print_info "Review manually to ensure no real secrets are committed"
    fi
}

test_dependencies() {
    print_section "10. Dependencies Check"
    
    print_test "Checking requirements.txt"
    if [ -f "requirements.txt" ]; then
        local package_count=$(wc -l < requirements.txt)
        print_success "requirements.txt has $package_count dependencies"
    else
        print_failure "requirements.txt is missing"
    fi
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        
        print_test "Checking if all dependencies are installed"
        if pip check > /dev/null 2>&1; then
            print_success "All dependencies are compatible"
        else
            print_warning "Some dependency conflicts detected"
            pip check 2>&1 | head -5
        fi
    else
        print_info "Virtual environment not found, skipping installed packages check"
    fi
}

test_api_structure() {
    print_section "11. API Structure Validation"
    
    print_test "Checking API endpoint files"
    local endpoints=(
        "app/api/v1/endpoints/businesses.py"
        "app/api/v1/endpoints/clients.py"
        "app/api/v1/endpoints/appointments.py"
        "app/api/v1/endpoints/communications.py"
        "app/api/v1/endpoints/notifications.py"
        "app/api/v1/endpoints/staff.py"
        "app/api/v1/endpoints/reviews.py"
        "app/api/v1/endpoints/favorites.py"
        "app/api/v1/endpoints/services.py"
        "app/api/v1/endpoints/websocket.py"
        "app/api/v1/endpoints/business_hours.py"
    )
    
    local missing_endpoints=0
    for endpoint in "${endpoints[@]}"; do
        if [ ! -f "$endpoint" ]; then
            print_failure "Missing: $endpoint"
            ((missing_endpoints++))
        fi
    done
    
    if [ $missing_endpoints -eq 0 ]; then
        print_success "All endpoint files present (${#endpoints[@]} endpoints)"
    else
        print_failure "Missing $missing_endpoints endpoint file(s)"
    fi
    
    print_test "Checking models"
    local models=(
        "app/models/clients.py"
        "app/models/businesses.py"
        "app/models/appointments.py"
        "app/models/communications.py"
        "app/models/notifications.py"
        "app/models/staff.py"
        "app/models/reviews.py"
        "app/models/favorites.py"
        "app/models/payments.py"
    )
    
    local missing_models=0
    for model in "${models[@]}"; do
        if [ ! -f "$model" ]; then
            print_failure "Missing: $model"
            ((missing_models++))
        fi
    done
    
    if [ $missing_models -eq 0 ]; then
        print_success "All model files present (${#models[@]} models)"
    else
        print_failure "Missing $missing_models model file(s)"
    fi
}

test_celery_tasks() {
    print_section "12. Celery Tasks Check"
    
    local tasks=(
        "app/tasks/appointment_tasks.py"
        "app/tasks/notification_tasks.py"
        "app/tasks/review_tasks.py"
        "app/tasks/maintenance_tasks.py"
    )
    
    local missing_tasks=0
    for task in "${tasks[@]}"; do
        print_test "Checking $(basename "$task")"
        if [ -f "$task" ]; then
            print_success "$(basename "$task") exists"
        else
            print_failure "Missing: $task"
            ((missing_tasks++))
        fi
    done
    
    if [ $missing_tasks -eq 0 ]; then
        print_success "All Celery task files present"
    fi
}

###############################################################################
# Summary and Results
###############################################################################

print_summary() {
    print_section "Test Summary"
    
    local pass_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                   TEST RESULTS                         ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Total Tests:     ${TOTAL_TESTS}"
    echo -e "${CYAN}║${NC}  ${GREEN}Passed:${NC}          ${PASSED_TESTS}"
    echo -e "${CYAN}║${NC}  ${RED}Failed:${NC}          ${FAILED_TESTS}"
    echo -e "${CYAN}║${NC}  Pass Rate:       ${pass_rate}%"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    
    echo ""
    
    if [ "$TEST_FAILED" = true ]; then
        echo -e "${RED}❌ Some tests failed!${NC}"
        echo -e "${YELLOW}Please fix the issues before pushing to git.${NC}"
        echo ""
        echo -e "${CYAN}Common fixes:${NC}"
        echo "  • Run: pip install -r requirements.txt"
        echo "  • Run: python3 validate_env.py"
        echo "  • Check syntax errors in failed files"
        echo "  • Ensure all required files exist"
        echo ""
        return 1
    else
        echo -e "${GREEN}✅ All tests passed!${NC}"
        echo -e "${GREEN}Your code is ready to push to git! 🚀${NC}"
        echo ""
        echo -e "${CYAN}Next steps:${NC}"
        echo "  1. Review your changes: git status"
        echo "  2. Stage your files: git add ."
        echo "  3. Commit: git commit -m 'Your message'"
        echo "  4. Push: git push origin <branch>"
        echo ""
        return 0
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_banner
    
    echo -e "${CYAN}Running comprehensive pre-push tests...${NC}"
    echo -e "${CYAN}This will take a moment...${NC}\n"
    
    # Run all test suites
    test_python_syntax
    test_imports
    test_environment_config
    test_required_files
    test_automation_scripts
    test_docker_config
    test_git_status
    test_documentation
    test_security
    test_dependencies
    test_api_structure
    test_celery_tasks
    
    # Print summary and exit with appropriate code
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Trap interrupts
trap 'echo -e "\n${YELLOW}⏸️  Tests interrupted${NC}"; exit 130' INT

# Run main
main

