# Firebase Cloud Messaging (FCM) HTTP v1 Setup Guide

Firebase has deprecated the legacy FCM server key API and now requires the HTTP v1 API for push notifications. This guide shows you how to configure FCM for the Bookora application.

## 🔥 What Changed

- **Legacy FCM API**: Deprecated on 6/20/2023, disabled by default for new projects
- **New HTTP v1 API**: Uses OAuth2 authentication with service account credentials
- **Benefits**: Better security, more features, unified with other Firebase services

## 📱 Firebase Console Setup

### 1. Enable Cloud Messaging
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Cloud Messaging**
4. Copy the **Sender ID** (this is what you need for `.env`)

### 2. Service Account (Already Done)
The FCM HTTP v1 API uses the same service account credentials as Firebase Auth, so if you've already set up Firebase authentication, you're good to go!

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
# Firebase Auth (required for FCM)
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
# ... other Firebase auth variables

# FCM Configuration
FCM_SENDER_ID=123456789012  # From Firebase Console > Cloud Messaging
FCM_PROJECT_ID=your-firebase-project-id  # Usually same as FIREBASE_PROJECT_ID
```

### How to Get Sender ID
1. Firebase Console → Project Settings
2. Click **Cloud Messaging** tab
3. Copy the **Sender ID** number
4. Add to your `.env` as `FCM_SENDER_ID`

## 🚀 Usage Examples

### Send Appointment Reminder
```python
from app.services.fcm_service import send_appointment_notification

# Send reminder notification
await send_appointment_notification(
    fcm_token="user_device_fcm_token",
    business_name="Hair Salon Pro",
    appointment_date="2025-11-15 10:00 AM",
    notification_type="reminder"
)
```

### Send Chat Message Notification
```python
from app.services.fcm_service import send_chat_notification

await send_chat_notification(
    fcm_token="user_device_fcm_token",
    sender_name="Hair Salon Pro",
    message_preview="Your appointment has been confirmed!"
)
```

### Custom Notification
```python
from app.services.fcm_service import FCMMessage, fcm_service

message = FCMMessage(
    token="user_device_fcm_token",
    title="Welcome to Bookora!",
    body="Start booking appointments with local businesses",
    data={"type": "welcome", "action": "onboarding"},
    click_action="MAIN_ACTIVITY"
)

success = await fcm_service.send_notification(message)
```

## 📱 Frontend Integration

### Android (Kotlin/Java)
```kotlin
// Get FCM token
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (!task.isSuccessful) {
        Log.w(TAG, "Fetching FCM registration token failed", task.exception)
        return@addOnCompleteListener
    }

    // Get new FCM registration token
    val token = task.result
    Log.d(TAG, "FCM Token: $token")
    
    // Send token to your server
    sendTokenToServer(token)
}
```

### iOS (Swift)
```swift
import FirebaseMessaging

// Get FCM token
Messaging.messaging().token { token, error in
    if let error = error {
        print("Error fetching FCM registration token: \(error)")
    } else if let token = token {
        print("FCM registration token: \(token)")
        // Send token to your server
        sendTokenToServer(token)
    }
}
```

### React Native
```javascript
import messaging from '@react-native-firebase/messaging';

// Get FCM token
const getFcmToken = async () => {
  try {
    const token = await messaging().getToken();
    console.log('FCM Token:', token);
    // Send token to your server
    sendTokenToServer(token);
  } catch (error) {
    console.error('Error getting FCM token:', error);
  }
};
```

### Flutter
```dart
import 'package:firebase_messaging/firebase_messaging.dart';

// Get FCM token
Future<void> getFcmToken() async {
  String? token = await FirebaseMessaging.instance.getToken();
  print('FCM Token: $token');
  // Send token to your server
  sendTokenToServer(token);
}
```

## 🔧 API Endpoints

### Update FCM Token
```bash
POST /api/v1/notifications/fcm-token
{
  "fcm_token": "user_device_token_here"
}
```

### Send Test Notification
```bash
POST /api/v1/notifications/send-test
{
  "title": "Test Notification",
  "body": "This is a test message",
  "data": {"test": "true"}
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **"Service account not found"**
   - Ensure Firebase service account JSON is properly configured
   - Check that all Firebase environment variables are set

2. **"Invalid project ID"**
   - Verify `FCM_PROJECT_ID` matches your Firebase project
   - Check `FIREBASE_PROJECT_ID` is correct

3. **"Token not found"**
   - Ensure client app has obtained FCM token
   - Check token is sent to server and stored properly

4. **"Authentication failed"**
   - Verify service account has proper permissions
   - Check private key format (escaped newlines: `\\n`)

### Testing FCM
```python
# Test FCM configuration
from app.services.fcm_service import fcm_service

# This will validate credentials without sending
try:
    token = fcm_service._get_access_token()
    print("✅ FCM credentials valid")
except Exception as e:
    print(f"❌ FCM error: {e}")
```

## 📊 Monitoring

### Firebase Console
- Go to Cloud Messaging → Reports
- View delivery statistics
- Monitor notification performance

### Application Logs
```python
import logging
logger = logging.getLogger(__name__)

# FCM service automatically logs:
# - Successful notifications
# - Failed notifications with error details
# - Bulk notification summaries
```

## 🔐 Security Best Practices

1. **Service Account Security**
   - Never commit service account JSON to Git
   - Use environment variables in production
   - Rotate service account keys regularly

2. **Token Management**
   - Store FCM tokens securely
   - Remove tokens for uninstalled apps
   - Validate tokens before sending notifications

3. **Rate Limiting**
   - Implement notification rate limits
   - Avoid spam notifications
   - Respect user preferences

## ✅ Migration Checklist

- [ ] Copy Sender ID from Firebase Console
- [ ] Update `.env` with `FCM_SENDER_ID`
- [ ] Remove old `FCM_SERVER_KEY` references
- [ ] Test notification sending
- [ ] Update frontend apps to use current Firebase SDK
- [ ] Monitor notification delivery in Firebase Console

The Bookora FCM service is now ready for modern push notifications! 🚀