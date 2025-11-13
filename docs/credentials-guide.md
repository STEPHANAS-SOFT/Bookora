# Credentials Management Guide

## Overview

Bookora uses a centralized credentials management system where all configuration and credentials are managed in a single place through environment variables and accessed via the `CredentialsManager` class.

## Key Benefits

✅ **Single Source of Truth**: All credentials in `.env` file  
✅ **Type Safety**: Pydantic validation ensures correct types  
✅ **Environment Aware**: Different configs for dev/prod/test  
✅ **Secure**: No hardcoded credentials in code  
✅ **Easy Access**: Simple API to get any configuration  

## Quick Usage

### 1. Basic Configuration Access

```python
from app.core.credentials import credentials, get_database_url, get_redis_url

# Get database URL
db_url = get_database_url()

# Get Redis URL  
redis_url = get_redis_url()

# Get email configuration
email_config = credentials.get_email_config()
smtp_host = email_config["host"]
smtp_port = email_config["port"]
```

### 2. Firebase Credentials

```python
from app.core.credentials import get_firebase_credentials

# Get Firebase credentials as dictionary
firebase_creds = get_firebase_credentials()

# Or get as temporary file (useful for some Firebase SDKs)
temp_file_path = credentials.get_firebase_credentials_file()
```

### 3. Environment Detection

```python
from app.core.credentials import is_development, is_production

if is_development():
    print("Running in development mode")
    
if is_production():
    print("Running in production mode")
```

### 4. Specific Configuration Groups

```python
from app.core.credentials import credentials

# Get all database configuration
db_config = credentials.get_database_config()

# Get security configuration
security = credentials.get_security_config()
secret_key = security["secret_key"]

# Get business logic configuration
business = credentials.get_business_config()
appointment_duration = business["default_appointment_duration"]

# Get file upload configuration
upload = credentials.get_file_upload_config()
max_size = upload["max_size"]
```

## Configuration Categories

### Environment & Security
- `ENVIRONMENT`: development/production/testing
- `DEBUG`: Enable debug mode
- `SECRET_KEY`: JWT signing key
- `ALGORITHM`: JWT algorithm
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration

### Database (PostgreSQL)
- `DATABASE_URL`: Complete connection string
- `DATABASE_HOST`: Database host
- `DATABASE_PORT`: Database port
- `DATABASE_NAME`: Database name
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password

### Firebase Authentication
- `FIREBASE_PROJECT_ID`: Firebase project ID
- `FIREBASE_PRIVATE_KEY`: Service account private key
- `FIREBASE_CLIENT_EMAIL`: Service account email
- All other Firebase service account fields

### Email (SMTP)
- `SMTP_HOST`: SMTP server host
- `SMTP_PORT`: SMTP server port
- `SMTP_USERNAME`: SMTP username
- `SMTP_PASSWORD`: SMTP password
- `FROM_EMAIL`: Default from email
- `FROM_NAME`: Default from name

### Other Services
- `REDIS_URL`: Redis connection string
- `FCM_SERVER_KEY`: Firebase Cloud Messaging key
- `MAX_FILE_SIZE`: Maximum file upload size
- `UPLOAD_DIR`: File upload directory

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your actual values:
   ```bash
   # Edit the file with your credentials
   nano .env
   ```

3. The application will automatically load and validate all configurations on startup.

## Best Practices

### ✅ Do's
- Use the `credentials` manager to access all configuration
- Set environment variables in `.env` file
- Use type-safe access methods when available
- Check environment with `is_development()` for conditional logic

### ❌ Don'ts
- Don't access `os.environ` directly for app config
- Don't hardcode credentials in source code
- Don't commit `.env` files to version control
- Don't access `settings` object directly from other modules

## Example Integration

Here's how a typical service might use the credentials system:

```python
# services/email_service.py
from app.core.credentials import credentials, is_development

class EmailService:
    def __init__(self):
        config = credentials.get_email_config()
        self.smtp_host = config["host"]
        self.smtp_port = config["port"]
        self.username = config["username"]
        self.password = config["password"]
        self.from_email = config["from_email"]
        self.from_name = config["from_name"]
        
    async def send_email(self, to: str, subject: str, body: str):
        if is_development():
            print(f"DEV MODE: Would send email to {to}")
            return
            
        # Actual email sending logic here
        pass
```

This approach ensures that:
- All credentials are managed in one place
- The code is environment-aware
- Configuration is type-safe and validated
- Easy to test and maintain