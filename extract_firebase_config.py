#!/usr/bin/env python3
"""
Firebase Configuration Extractor
Run this script to extract Firebase config from service account JSON
"""

import json
import sys

def extract_firebase_config():
    """Extract Firebase configuration from service account JSON file"""
    
    if len(sys.argv) != 2:
        print("Usage: python extract_firebase_config.py <path-to-service-account.json>")
        print("Example: python extract_firebase_config.py ./firebase-service-account.json")
        return
    
    json_file_path = sys.argv[1]
    
    try:
        with open(json_file_path, 'r') as file:
            config = json.load(file)
        
        print("Copy these values to your .env file:")
        print("=" * 50)
        print(f'FIREBASE_PROJECT_ID={config.get("project_id", "")}')
        print(f'FIREBASE_PRIVATE_KEY_ID={config.get("private_key_id", "")}')
        
        # Handle private key with proper escaping
        private_key = config.get("private_key", "").replace('\n', '\\n')
        print(f'FIREBASE_PRIVATE_KEY="{private_key}"')
        
        print(f'FIREBASE_CLIENT_EMAIL={config.get("client_email", "")}')
        print(f'FIREBASE_CLIENT_ID={config.get("client_id", "")}')
        print(f'FIREBASE_AUTH_URI={config.get("auth_uri", "")}')
        print(f'FIREBASE_TOKEN_URI={config.get("token_uri", "")}')
        print(f'FIREBASE_AUTH_PROVIDER_X509_CERT_URL={config.get("auth_provider_x509_cert_url", "")}')
        print(f'FIREBASE_CLIENT_X509_CERT_URL={config.get("client_x509_cert_url", "")}')
        
        print("=" * 50)
        print("✅ Configuration extracted successfully!")
        print("")
        print("📱 FCM Setup (HTTP v1 API):")
        print("1. Go to Firebase Console > Project Settings > Cloud Messaging")
        print("2. Copy the 'Sender ID' and add it to your .env as FCM_SENDER_ID")
        print("3. The service account JSON above is used for FCM HTTP v1 API")
        print("4. No legacy FCM server key needed!")
        print("")
        print("💡 Note: FCM now uses the same service account credentials for push notifications")
        
    except FileNotFoundError:
        print(f"❌ Error: File '{json_file_path}' not found")
    except json.JSONDecodeError:
        print("❌ Error: Invalid JSON file")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    extract_firebase_config()