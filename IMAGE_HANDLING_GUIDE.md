# 📸 Image Handling Guide - Bookora API

This guide explains how images are handled in the Bookora API and how to implement image upload/display in FlutterFlow.

---

## 🖼️ Image URL Fields Summary

### **1. Client Profile Images**

#### Model: `Client`
- **Field**: `profile_image_url` (String, 500 chars max)
- **Purpose**: User profile picture
- **Endpoints**:
  - Get: `GET /clients/me` - Returns client profile with `profile_image_url`
  - Update: `PUT /clients/me` - Update profile including `profile_image_url`

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "profile_image_url": "https://firebasestorage.googleapis.com/v0/b/..."
}
```

---

### **2. Business Images**

#### Model: `Business`
- **Field 1**: `logo_url` (String, 500 chars max) - Business logo
- **Field 2**: `cover_image_url` (String, 500 chars max) - Cover/banner image
- **Purpose**: Main business branding images
- **Endpoints**:
  - Get: `GET /businesses/me` - Returns business with `logo_url` and `cover_image_url`
  - Get Public: `GET /businesses/{business_id}` - Public view
  - Update: `PUT /businesses/me` - Update business including image URLs

```json
{
  "name": "Elite Hair Salon",
  "logo_url": "https://firebasestorage.googleapis.com/v0/b/.../logo.png",
  "cover_image_url": "https://firebasestorage.googleapis.com/v0/b/.../cover.jpg"
}
```

---

### **3. Business Gallery (Multiple Images)**

#### Model: `BusinessGallery`
- **Purpose**: Showcase business with multiple photos (interior, exterior, work samples, team, etc.)
- **Image Types**: exterior, interior, work_sample, team, product, event, etc.
- **Features**:
  - Multiple images per business
  - Image title and description
  - Sort order for gallery display
  - Primary/featured image flag
  - Active/inactive status
  - Image type categorization

#### Endpoints:

**Add Image to Gallery:**
```http
POST /businesses/gallery/add?firebase_uid={uid}
Content-Type: application/json

{
  "image_url": "https://firebasestorage.googleapis.com/v0/b/.../gallery1.jpg",
  "image_title": "Our Modern Interior",
  "image_description": "Recently renovated space with natural lighting",
  "sort_order": 1,
  "is_primary": true,
  "image_type": "interior"
}
```

**Get Business Gallery (Public):**
```http
GET /businesses/gallery?business_id={business_id}&active_only=true
```

**Get My Business Gallery:**
```http
GET /businesses/gallery/my?firebase_uid={uid}
```

**Update Gallery Image:**
```http
PUT /businesses/gallery/{image_id}?firebase_uid={uid}
Content-Type: application/json

{
  "image_title": "Updated Title",
  "sort_order": 2,
  "is_active": false
}
```

**Delete Gallery Image:**
```http
DELETE /businesses/gallery/{image_id}?firebase_uid={uid}
```

---

### **4. Service Images**

#### Model: `Service`
- **Field**: `service_image_url` (String, 500 chars max)
- **Purpose**: Primary service image
- **Endpoints**:
  - Get: `GET /businesses/services?firebase_uid={uid}` - Returns all services with images
  - Create: `POST /businesses/services/create?firebase_uid={uid}` - Include `service_image_url`
  - Update: `PUT /businesses/services/{service_id}?firebase_uid={uid}` - Update including image

```json
{
  "name": "Haircut & Styling",
  "description": "Professional haircut with styling",
  "duration_minutes": 60,
  "price": 50.00,
  "service_image_url": "https://firebasestorage.googleapis.com/v0/b/.../haircut.jpg"
}
```

---

### **5. Service Gallery (Multiple Images)**

#### Model: `ServiceGallery`
- **Purpose**: Showcase service results with multiple photos (before/after, work samples, etc.)
- **Image Types**: before, after, in_progress, result, sample, example, etc.
- **Features**:
  - Multiple images per service
  - Perfect for before/after galleries
  - Image title and description
  - Sort order for gallery display
  - Primary/featured image flag
  - Active/inactive status
  - Image type categorization

#### Endpoints:

**Add Image to Service Gallery:**
```http
POST /businesses/services/{service_id}/gallery/add?firebase_uid={uid}
Content-Type: application/json

{
  "image_url": "https://firebasestorage.googleapis.com/v0/b/.../before.jpg",
  "image_title": "Before Treatment",
  "image_description": "Client hair before the transformation",
  "sort_order": 1,
  "is_primary": false,
  "image_type": "before"
}
```

**Get Service Gallery (Public):**
```http
GET /businesses/services/{service_id}/gallery?active_only=true
```

**Update Service Gallery Image:**
```http
PUT /businesses/services/gallery/{image_id}?firebase_uid={uid}
Content-Type: application/json

{
  "image_title": "After Treatment",
  "image_type": "after",
  "sort_order": 2
}
```

**Delete Service Gallery Image:**
```http
DELETE /businesses/services/gallery/{image_id}?firebase_uid={uid}
```

---

## 🚀 FlutterFlow Implementation Guide

### **Step 1: Image Upload Flow**

1. **User selects image** from device (Camera or Gallery)
2. **Upload to Firebase Storage** using FlutterFlow's Firebase Storage integration
3. **Get download URL** from Firebase Storage
4. **Send URL to Bookora API** using the appropriate endpoint

### **Step 2: FlutterFlow Setup**

#### A. Upload Image Widget Flow

```
┌─────────────────────────────────────────────────────┐
│ 1. Image Picker Widget (Camera/Gallery)            │
│    ↓                                                │
│ 2. Upload to Firebase Storage Action               │
│    - Path: /businesses/{business_id}/profile.jpg   │
│    - Get download URL: saveToState(imageUrl)       │
│    ↓                                                │
│ 3. API Call Action (Bookora API)                   │
│    - Method: PUT                                     │
│    - URL: {baseUrl}/businesses/me                   │
│    - Headers: X-API-Key                             │
│    - Body: {"logo_url": "{imageUrl}"}              │
└─────────────────────────────────────────────────────┘
```

#### B. Display Gallery Images

```dart
// FlutterFlow List View or GridView
// Data Source: API Call to /businesses/gallery?business_id={id}
// Item Template: NetworkImage Widget with gallery_image.image_url
```

---

## 📋 Best Practices

### **1. Image Size Optimization**

Before uploading to Firebase Storage:
- **Profile Images**: 512x512px, max 100KB
- **Logo Images**: 512x512px, max 100KB
- **Cover Images**: 1920x600px, max 500KB
- **Gallery Images**: 1280x720px, max 300KB
- **Service Images**: 800x600px, max 200KB

### **2. Image Naming Convention**

```
Firebase Storage Path Structure:
/businesses/{business_id}/
  ├── logo.jpg
  ├── cover.jpg
  └── gallery/
      ├── gallery_1.jpg
      ├── gallery_2.jpg
      └── ...

/services/{service_id}/
  └── gallery/
      ├── before_1.jpg
      ├── after_1.jpg
      └── ...

/clients/{client_id}/
  └── profile.jpg
```

### **3. Error Handling**

```dart
// FlutterFlow Action Chain
try {
  // 1. Upload to Firebase Storage
  uploadedUrl = await uploadToFirebase(imagePath);
  
  // 2. Call Bookora API
  apiResponse = await updateBusiness(logoUrl: uploadedUrl);
  
  // 3. Show success message
  showSnackbar("Image uploaded successfully!");
  
} catch (error) {
  // 4. Handle errors
  showSnackbar("Failed to upload image: ${error}");
  // Optionally delete from Firebase Storage if API call fails
}
```

### **4. Image Deletion**

**Important**: When deleting gallery images:
1. **First**: Delete from Bookora API (removes database record)
2. **Then**: Delete from Firebase Storage (removes actual file)
3. This prevents orphaned files in Firebase Storage

```dart
// FlutterFlow Action Chain for Delete
try {
  // 1. Delete from Bookora API
  await deleteGalleryImage(imageId);
  
  // 2. Delete from Firebase Storage
  await deleteFromFirebase(imageUrl);
  
  // 3. Refresh gallery list
  refreshGalleryList();
  
} catch (error) {
  showSnackbar("Failed to delete image: ${error}");
}
```

---

## 🔐 Security Considerations

### **1. Firebase Storage Rules**

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Authenticated users can upload/read their own images
    match /clients/{clientId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == clientId;
    }
    
    match /businesses/{businessId}/{allPaths=**} {
      allow read: if true; // Public read for business images
      allow write: if request.auth != null; // Only authenticated users can upload
    }
    
    match /services/{serviceId}/{allPaths=**} {
      allow read: if true; // Public read for service images
      allow write: if request.auth != null;
    }
  }
}
```

### **2. Image URL Validation**

The API validates:
- ✅ URL format (must be valid HTTPS URL)
- ✅ Max length (500 characters)
- ✅ Firebase UID authorization (users can only update their own images)

---

## 📊 Database Schema

### **Image-Related Tables:**

```sql
-- Clients: 1 profile image
clients (
  id UUID PRIMARY KEY,
  profile_image_url VARCHAR(500)
);

-- Businesses: 2 main images + gallery
businesses (
  id UUID PRIMARY KEY,
  logo_url VARCHAR(500),
  cover_image_url VARCHAR(500)
);

business_gallery (
  id UUID PRIMARY KEY,
  business_id UUID REFERENCES businesses(id),
  image_url VARCHAR(500) NOT NULL,
  image_title VARCHAR(200),
  image_description TEXT,
  sort_order INTEGER DEFAULT 0,
  is_primary BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,
  image_type VARCHAR(50)
);

-- Services: 1 primary image + gallery
services (
  id UUID PRIMARY KEY,
  business_id UUID REFERENCES businesses(id),
  service_image_url VARCHAR(500)
);

service_gallery (
  id UUID PRIMARY KEY,
  service_id UUID REFERENCES services(id),
  image_url VARCHAR(500) NOT NULL,
  image_title VARCHAR(200),
  image_description TEXT,
  sort_order INTEGER DEFAULT 0,
  is_primary BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,
  image_type VARCHAR(50)
);
```

---

## 🎯 Use Cases

### **Business Owner:**
1. **Profile Setup**: Upload logo and cover image during registration
2. **Gallery Management**: Add multiple photos showcasing business
3. **Service Showcase**: Add service images and before/after galleries
4. **Update Images**: Replace or reorder gallery images

### **Client:**
1. **View Business**: See business logo, cover, and gallery when browsing
2. **View Services**: See service images and galleries when selecting services
3. **Profile**: Upload and update their own profile picture

---

## 🆘 Troubleshooting

### **Issue: Image not displaying**
- ✅ Check if URL is valid and accessible
- ✅ Verify Firebase Storage permissions
- ✅ Ensure URL uses HTTPS (not HTTP)
- ✅ Check if image was marked as `is_active: false`

### **Issue: Upload fails**
- ✅ Check Firebase Storage quota
- ✅ Verify file size (max recommended: 5MB per image)
- ✅ Ensure valid API key in request headers
- ✅ Check Firebase UID is correct

### **Issue: Gallery images out of order**
- ✅ Use `sort_order` field to control display order
- ✅ Update `sort_order` values using PUT endpoint
- ✅ Order by `sort_order` ASC when fetching

---

## 📈 Statistics

### **Total Image Capabilities:**
- **3** Single image fields (client profile, business logo, business cover)
- **1** Service primary image field
- **2** Gallery systems (business gallery, service gallery)
- **Unlimited** images per business/service through galleries

### **API Endpoints for Images:**
- **Client**: 2 endpoints (get, update)
- **Business**: 3 endpoints (get, update, get public)
- **Business Gallery**: 5 endpoints (add, get, get my, update, delete)
- **Service**: 4 endpoints (get all, create, update, delete)
- **Service Gallery**: 5 endpoints (add, get, update, delete)
- **Total**: **19 image-related endpoints** 📸

---

## ✨ Summary

The Bookora API provides **comprehensive image support** for:
- ✅ **Client profiles** with profile pictures
- ✅ **Business branding** with logo and cover images
- ✅ **Business galleries** with unlimited photos
- ✅ **Service images** for each service
- ✅ **Service galleries** with unlimited before/after photos

All images are stored as URLs pointing to Firebase Storage, making the system:
- 🚀 Fast and scalable
- 💰 Cost-effective
- 🔐 Secure with Firebase security rules
- 📱 Perfect for mobile apps

---

**Need help?** Check the [FLUTTERFLOW_INTEGRATION_GUIDE.md](./FLUTTERFLOW_INTEGRATION_GUIDE.md) for detailed integration steps! 🎉

