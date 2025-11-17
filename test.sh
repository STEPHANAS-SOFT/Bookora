#!/bin/bash
###############################################################################
# Bookora Backend - Automated Testing Script
#
# This script runs automated tests for the Bookora backend including:
# - Unit tests
# - Integration tests
# - API endpoint tests
# - Code quality checks
# - Coverage reports
#
# Usage:
#   ./test.sh [options]
#
# Options:
#   --unit              Run only unit tests
#   --integration       Run only integration tests
#   --api               Run only API tests
#   --coverage          Generate coverage report
#   --verbose           Verbose output
#   --fast              Skip slow tests
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
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_TYPE="all"
GENERATE_COVERAGE=false
VERBOSE=false
FAST=false

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║          🧪 AUTOMATED TESTING SYSTEM 🧪                  ║"
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

###############################################################################
# Parse Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --api)
            TEST_TYPE="api"
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        --help)
            echo "Usage: ./test.sh [options]"
            echo ""
            echo "Options:"
            echo "  --unit              Run only unit tests"
            echo "  --integration       Run only integration tests"
            echo "  --api               Run only API tests"
            echo "  --coverage          Generate coverage report"
            echo "  --verbose           Verbose output"
            echo "  --fast              Skip slow tests"
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
# Test Functions
###############################################################################

setup_test_environment() {
    print_section "Setting Up Test Environment"
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        print_info "Activating virtual environment..."
        source venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_warning "No virtual environment found"
    fi
    
    # Check if pytest is installed
    if ! python3 -c "import pytest" 2>/dev/null; then
        print_info "Installing pytest..."
        pip install pytest pytest-cov pytest-asyncio httpx --quiet
        print_success "Test dependencies installed"
    else
        print_success "Pytest is installed"
    fi
    
    # Set test environment variables
    export TESTING=true
    export DATABASE_URL="postgresql://bookora_user:bookora_password@localhost:5432/bookora_test"
    print_info "Test environment configured"
}

create_test_database() {
    print_section "Preparing Test Database"
    
    # Load env vars
    if [ -f ".env" ]; then
        export $(grep -v '^#' ".env" | xargs 2>/dev/null)
    fi
    
    local db_host=${DATABASE_HOST:-localhost}
    local db_user=${DATABASE_USER:-bookora_user}
    local db_pass=${DATABASE_PASSWORD}
    local test_db="bookora_test"
    
    export PGPASSWORD="$db_pass"
    
    # Check if test database exists
    if psql -h "$db_host" -U "$db_user" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$test_db"; then
        print_info "Test database exists, dropping..."
        psql -h "$db_host" -U "$db_user" -c "DROP DATABASE IF EXISTS $test_db;" 2>/dev/null || true
    fi
    
    # Create test database
    print_info "Creating test database..."
    psql -h "$db_host" -U "$db_user" -c "CREATE DATABASE $test_db;" 2>/dev/null || {
        print_warning "Could not create test database (may already exist or no permissions)"
        return 0
    }
    
    print_success "Test database ready"
}

run_unit_tests() {
    print_section "Running Unit Tests"
    
    local pytest_args="-v"
    
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -vv"
    fi
    
    if [ "$FAST" = true ]; then
        pytest_args="$pytest_args -m 'not slow'"
    fi
    
    if [ "$GENERATE_COVERAGE" = true ]; then
        pytest_args="$pytest_args --cov=app --cov-report=html --cov-report=term"
    fi
    
    if [ -d "tests/unit" ]; then
        print_info "Running unit tests..."
        python3 -m pytest tests/unit $pytest_args
        print_success "Unit tests completed"
    else
        print_warning "No unit tests found (tests/unit directory missing)"
    fi
}

run_integration_tests() {
    print_section "Running Integration Tests"
    
    local pytest_args="-v"
    
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -vv"
    fi
    
    if [ "$FAST" = true ]; then
        pytest_args="$pytest_args -m 'not slow'"
    fi
    
    if [ -d "tests/integration" ]; then
        print_info "Running integration tests..."
        python3 -m pytest tests/integration $pytest_args
        print_success "Integration tests completed"
    else
        print_warning "No integration tests found (tests/integration directory missing)"
    fi
}

run_api_tests() {
    print_section "Running API Tests"
    
    # Start API server for testing (if not already running)
    local api_started=false
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_info "Starting test API server..."
        nohup python3 -m uvicorn app.main:app --port 8000 > /dev/null 2>&1 &
        local api_pid=$!
        api_started=true
        
        # Wait for API to be ready
        local attempts=0
        while [ $attempts -lt 30 ]; do
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                break
            fi
            sleep 1
            ((attempts++))
        done
        
        if [ $attempts -eq 30 ]; then
            print_error "API server failed to start"
            return 1
        fi
        
        print_success "Test API server started"
    fi
    
    local pytest_args="-v"
    
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -vv"
    fi
    
    if [ -d "tests/api" ]; then
        print_info "Running API tests..."
        python3 -m pytest tests/api $pytest_args
        print_success "API tests completed"
    else
        print_warning "No API tests found (tests/api directory missing)"
    fi
    
    # Stop test API server if we started it
    if [ "$api_started" = true ]; then
        print_info "Stopping test API server..."
        kill $api_pid 2>/dev/null || true
    fi
}

run_all_tests() {
    print_section "Running All Tests"
    
    local pytest_args="-v"
    
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -vv"
    fi
    
    if [ "$FAST" = true ]; then
        pytest_args="$pytest_args -m 'not slow'"
    fi
    
    if [ "$GENERATE_COVERAGE" = true ]; then
        pytest_args="$pytest_args --cov=app --cov-report=html --cov-report=term"
    fi
    
    if [ -d "tests" ]; then
        print_info "Running all tests..."
        python3 -m pytest tests/ $pytest_args
        print_success "All tests completed"
    else
        print_warning "No tests directory found"
        print_info "Creating basic test structure..."
        
        # Create test directories
        mkdir -p tests/unit tests/integration tests/api
        
        # Create conftest.py
        cat > tests/conftest.py << 'EOF'
"""
Pytest configuration and fixtures for Bookora tests.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def api_key():
    """Test API key."""
    return "bookora-dev-api-key-2025"
EOF
        
        # Create a sample test
        cat > tests/test_main.py << 'EOF'
"""
Basic tests for Bookora API.
"""

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_api_docs():
    """Test API documentation is accessible."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
EOF
        
        print_success "Test structure created"
        print_info "Running newly created tests..."
        python3 -m pytest tests/ $pytest_args
    fi
}

check_code_quality() {
    print_section "Running Code Quality Checks"
    
    # Check if flake8 is installed
    if command -v flake8 &> /dev/null; then
        print_info "Running flake8..."
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics || {
            print_warning "Flake8 found some issues"
        }
    else
        print_info "flake8 not installed (optional)"
    fi
    
    # Check if black is installed
    if command -v black &> /dev/null; then
        print_info "Checking code formatting with black..."
        black --check app/ || {
            print_warning "Code formatting issues found (run 'black app/' to fix)"
        }
    else
        print_info "black not installed (optional)"
    fi
}

generate_coverage_report() {
    if [ "$GENERATE_COVERAGE" = false ]; then
        return 0
    fi
    
    print_section "Generating Coverage Report"
    
    if [ -d "htmlcov" ]; then
        print_success "Coverage report generated: htmlcov/index.html"
        print_info "Open with: open htmlcov/index.html"
    else
        print_warning "Coverage report not generated"
    fi
}

print_summary() {
    print_section "Test Summary"
    
    echo -e "${GREEN}✅ Testing completed!${NC}\n"
    
    if [ "$GENERATE_COVERAGE" = true ] && [ -f ".coverage" ]; then
        echo -e "${CYAN}📊 Coverage Report:${NC}"
        python3 -m coverage report --skip-empty || true
        echo ""
    fi
    
    echo -e "${CYAN}💡 Useful Commands:${NC}"
    echo -e "   • Run specific test: pytest tests/test_file.py::test_function"
    echo -e "   • Run with coverage: ./test.sh --coverage"
    echo -e "   • Run only fast tests: ./test.sh --fast"
    echo -e "   • Verbose output: ./test.sh --verbose"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_banner
    
    print_info "Test type: $TEST_TYPE"
    
    # Setup
    setup_test_environment
    
    # Optional: Create test database
    # create_test_database
    
    # Run tests based on type
    case "$TEST_TYPE" in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        api)
            run_api_tests
            ;;
        all)
            run_all_tests
            ;;
        *)
            print_error "Invalid test type: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Optional quality checks
    # check_code_quality
    
    # Generate coverage report
    generate_coverage_report
    
    # Print summary
    print_summary
}

# Error handler
error_handler() {
    print_error "Tests failed at line $1"
    exit 1
}

trap 'error_handler $LINENO' ERR
trap 'echo -e "\n${YELLOW}⏸️  Tests interrupted${NC}"; exit 130' INT

# Run main
main

exit 0

