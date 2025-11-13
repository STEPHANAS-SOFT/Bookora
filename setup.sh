#!/bin/bash

# Bookora Development Setup Script
# This script sets up the development environment for the Bookora API

echo "🚀 Setting up Bookora development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.11+ is installed
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_success "Python $python_version is installed"
else
    print_error "Python 3.11+ is required. Current version: $python_version"
    exit 1
fi

# Create virtual environment
print_status "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

# Create .env file from example if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from example..."
    cp .env.example .env
    print_warning "Please update .env file with your actual configuration values"
else
    print_warning ".env file already exists"
fi

# Start Docker services
print_status "Starting Docker services (PostgreSQL, Redis, pgAdmin)..."
docker-compose up -d postgres redis pgadmin

# Wait for PostgreSQL to be ready
print_status "Waiting for PostgreSQL to be ready..."
sleep 10

# Run database migrations
print_status "Running database migrations..."
alembic upgrade head

print_success "Setup completed successfully!"
print_status "Next steps:"
echo "  1. Update .env file with your configuration"
echo "  2. Access pgAdmin at http://localhost:8080 (admin@bookora.com / admin123)"
echo "  3. Start the API: uvicorn main:app --reload"
echo "  4. API documentation: http://localhost:8000/docs"

print_warning "Remember to activate the virtual environment: source venv/bin/activate"