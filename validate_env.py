#!/usr/bin/env python3
"""
Bookora Backend - Environment Configuration Validator

This script validates the .env file to ensure all required environment
variables are set and properly configured before starting the application.

Usage:
    python validate_env.py

Features:
    - Checks for existence of .env file
    - Validates all required environment variables
    - Checks database connectivity
    - Tests Redis connection
    - Validates Firebase configuration (if provided)
    - Provides helpful error messages and suggestions

Author: Bookora Team
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class EnvValidator:
    """Validates environment configuration."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.env_vars: Dict[str, Optional[str]] = {}
        
    def print_banner(self):
        """Print validation banner."""
        print(f"{Colors.CYAN}")
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                                                           ║")
        print("║          🔍 ENVIRONMENT CONFIGURATION VALIDATOR 🔍       ║")
        print("║                                                           ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print(f"{Colors.NC}\n")
        
    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}  {title}{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")
        
    def print_success(self, message: str):
        """Print success message."""
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
        
    def print_error(self, message: str):
        """Print error message."""
        print(f"{Colors.RED}❌ {message}{Colors.NC}")
        self.errors.append(message)
        
    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")
        self.warnings.append(message)
        
    def print_info(self, message: str):
        """Print info message."""
        print(f"{Colors.CYAN}ℹ️  {message}{Colors.NC}")
        
    def check_env_file_exists(self) -> bool:
        """Check if .env file exists."""
        self.print_section("Checking Environment File")
        
        if not Path(".env").exists():
            self.print_error(".env file not found!")
            self.print_info("Copy .env.template to .env and fill in your values:")
            self.print_info("  cp .env.template .env")
            return False
            
        self.print_success(".env file found")
        return True
        
    def load_environment(self) -> bool:
        """Load environment variables from .env file."""
        try:
            load_dotenv()
            self.print_success("Environment variables loaded")
            return True
        except Exception as e:
            self.print_error(f"Failed to load .env file: {e}")
            return False
            
    def validate_required_vars(self):
        """Validate required environment variables."""
        self.print_section("Validating Required Variables")
        
        required_vars = {
            # Critical variables
            "SECRET_KEY": {
                "description": "Secret key for JWT tokens",
                "validator": lambda x: len(x) >= 32,
                "error": "SECRET_KEY must be at least 32 characters long"
            },
            "API_KEY": {
                "description": "API key for endpoint authentication",
                "validator": lambda x: len(x) >= 20,
                "error": "API_KEY must be at least 20 characters long"
            },
            "DATABASE_URL": {
                "description": "PostgreSQL database connection string",
                "validator": lambda x: x.startswith("postgresql://"),
                "error": "DATABASE_URL must start with 'postgresql://'"
            },
            "DATABASE_USER": {
                "description": "Database username",
                "validator": lambda x: len(x) > 0,
                "error": "DATABASE_USER cannot be empty"
            },
            "DATABASE_PASSWORD": {
                "description": "Database password",
                "validator": lambda x: len(x) > 0,
                "error": "DATABASE_PASSWORD cannot be empty"
            },
            "DATABASE_HOST": {
                "description": "Database host",
                "validator": lambda x: len(x) > 0,
                "error": "DATABASE_HOST cannot be empty"
            },
            "DATABASE_NAME": {
                "description": "Database name",
                "validator": lambda x: len(x) > 0,
                "error": "DATABASE_NAME cannot be empty"
            },
        }
        
        for var_name, config in required_vars.items():
            value = os.getenv(var_name)
            self.env_vars[var_name] = value
            
            if not value:
                self.print_error(f"{var_name} is not set")
                self.print_info(f"  {config['description']}")
            elif not config["validator"](value):
                self.print_error(config["error"])
            else:
                # Mask sensitive values
                if "PASSWORD" in var_name or "KEY" in var_name:
                    display_value = "*" * min(len(value), 20)
                else:
                    display_value = value[:50] + "..." if len(value) > 50 else value
                self.print_success(f"{var_name}: {display_value}")
                
    def validate_optional_vars(self):
        """Validate optional but recommended variables."""
        self.print_section("Validating Optional Variables")
        
        optional_vars = [
            ("REDIS_URL", "Redis connection for Celery"),
            ("FIREBASE_PROJECT_ID", "Firebase project for push notifications"),
            ("SMTP_HOST", "SMTP server for email notifications"),
            ("SMTP_USERNAME", "SMTP username"),
            ("CORS_ORIGINS", "Allowed CORS origins"),
        ]
        
        for var_name, description in optional_vars:
            value = os.getenv(var_name)
            self.env_vars[var_name] = value
            
            if not value:
                self.print_warning(f"{var_name} is not set")
                self.print_info(f"  {description}")
            else:
                self.print_success(f"{var_name} is set")
                
    def test_database_connection(self):
        """Test database connectivity."""
        self.print_section("Testing Database Connection")
        
        try:
            import psycopg2
            
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self.print_warning("DATABASE_URL not set, skipping test")
                return
                
            self.print_info("Attempting database connection...")
            
            # Parse connection string
            # Format: postgresql://user:password@host:port/database
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            self.print_success("Database connection successful")
            self.print_info(f"PostgreSQL version: {version.split(',')[0]}")
            
            cursor.close()
            conn.close()
            
        except ImportError:
            self.print_warning("psycopg2 not installed, skipping database test")
            self.print_info("Install with: pip install psycopg2-binary")
        except Exception as e:
            self.print_error(f"Database connection failed: {e}")
            self.print_info("Check your DATABASE_URL and ensure PostgreSQL is running")
            
    def test_redis_connection(self):
        """Test Redis connectivity."""
        self.print_section("Testing Redis Connection")
        
        try:
            import redis
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.print_info(f"Testing connection to: {redis_url}")
            
            r = redis.from_url(redis_url)
            r.ping()
            
            self.print_success("Redis connection successful")
            
            # Get Redis info
            info = r.info()
            self.print_info(f"Redis version: {info['redis_version']}")
            
        except ImportError:
            self.print_warning("redis package not installed, skipping test")
            self.print_info("Install with: pip install redis")
        except Exception as e:
            self.print_error(f"Redis connection failed: {e}")
            self.print_info("Ensure Redis is running: redis-server")
            
    def validate_firebase_config(self):
        """Validate Firebase configuration."""
        self.print_section("Validating Firebase Configuration")
        
        firebase_vars = [
            "FIREBASE_PROJECT_ID",
            "FIREBASE_PRIVATE_KEY",
            "FIREBASE_CLIENT_EMAIL"
        ]
        
        all_set = all(os.getenv(var) for var in firebase_vars)
        
        if all_set:
            self.print_success("Firebase configuration variables are set")
            
            # Validate private key format
            private_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            if "BEGIN PRIVATE KEY" in private_key:
                self.print_success("Firebase private key format is valid")
            else:
                self.print_warning("Firebase private key may be incorrectly formatted")
        else:
            self.print_warning("Firebase configuration incomplete")
            self.print_info("Push notifications will not work without Firebase setup")
            
    def validate_security_settings(self):
        """Validate security-related settings."""
        self.print_section("Validating Security Settings")
        
        environment = os.getenv("ENVIRONMENT", "development")
        debug = os.getenv("DEBUG", "True").lower() == "true"
        
        self.print_info(f"Environment: {environment}")
        self.print_info(f"Debug mode: {debug}")
        
        if environment == "production":
            if debug:
                self.print_error("DEBUG should be False in production!")
            else:
                self.print_success("DEBUG is correctly set to False for production")
                
            secret_key = os.getenv("SECRET_KEY", "")
            if "change" in secret_key.lower() or "secret" in secret_key.lower():
                self.print_error("SECRET_KEY appears to be using default value!")
            else:
                self.print_success("SECRET_KEY appears to be customized")
        else:
            self.print_info("Running in development mode")
            
    def print_summary(self):
        """Print validation summary."""
        self.print_section("Validation Summary")
        
        if not self.errors and not self.warnings:
            print(f"{Colors.GREEN}✅ All validation checks passed!{Colors.NC}\n")
            print(f"{Colors.CYAN}🚀 Your environment is properly configured.{Colors.NC}")
            print(f"{Colors.CYAN}   You can start the application with: ./start.sh{Colors.NC}\n")
            return True
        else:
            if self.errors:
                print(f"{Colors.RED}❌ Found {len(self.errors)} error(s):{Colors.NC}")
                for error in self.errors:
                    print(f"   • {error}")
                print()
                
            if self.warnings:
                print(f"{Colors.YELLOW}⚠️  Found {len(self.warnings)} warning(s):{Colors.NC}")
                for warning in self.warnings:
                    print(f"   • {warning}")
                print()
                
            if self.errors:
                print(f"{Colors.RED}❌ Please fix the errors before starting the application.{Colors.NC}\n")
                return False
            else:
                print(f"{Colors.YELLOW}⚠️  Application can start, but some features may not work.{Colors.NC}\n")
                return True
                
    def run(self) -> int:
        """Run all validation checks."""
        self.print_banner()
        
        # Check .env file
        if not self.check_env_file_exists():
            return 1
            
        # Load environment
        if not self.load_environment():
            return 1
            
        # Run validations
        self.validate_required_vars()
        self.validate_optional_vars()
        self.validate_security_settings()
        self.validate_firebase_config()
        
        # Test connections
        self.test_database_connection()
        self.test_redis_connection()
        
        # Print summary
        success = self.print_summary()
        
        return 0 if success else 1


def main():
    """Main entry point."""
    validator = EnvValidator()
    exit_code = validator.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

