# MedCloud Backend API Documentation

## Base URL
```
http://127.0.0.1:8000/api/
```

## Authentication
All authenticated endpoints require JWT token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

---

## 1. AUTHENTICATION ENDPOINTS

### 1.1 Patient Registration (Step 1 - Collect Details)
**POST** `/auth/register/patient/`

**Request:**
```json
{
  "full_name": "John Doe",
  "age": 30,
  "gender": "male",
  "phone_number": "+1234567890",
  "address": "123 Main St",
  "emergency_contact": "Jane Doe +0987654321",
  "email": "john@example.com"
}
```

**Response (201):**
```json
{
  "detail": "Patient registration started. OTP has been sent to the provided contact."
}
```

---

### 1.2 Patient OTP Verification (Step 2)
**POST** `/auth/register/patient/verify-otp/`

**Request:**
```json
{
  "email": "john@example.com",
  "code": "123456",
  "purpose": "registration"
}
```

**Response (200):**
```json
{
  "detail": "OTP verified. Complete your password setup to log in."
}
```

---

### 1.3 Patient Set Password (Step 3)
**POST** `/auth/register/patient/password/`

**Request:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "john@example.com",
    "username": "john",
    "role": "PATIENT",
    "phone_number": "+1234567890",
    "is_verified": true,
    "is_active": true,
    "created_at": "2026-05-21T10:00:00Z"
  }
}
```

---

### 1.4 Doctor Registration (Step 1)
**POST** `/auth/register/doctor/`

**Request:**
```json
{
  "full_name": "Dr. Smith",
  "hospital_name": "City Hospital",
  "specialization": "Cardiology",
  "medical_license_number": "MD123456",
  "years_of_experience": 10,
  "email": "dr.smith@example.com",
  "phone_number": "+1234567890"
}
```

**Response (201):**
```json
{
  "detail": "Doctor registration submitted. OTP has been sent for mobile/email verification."
}
```

---

### 1.5 Doctor OTP Verification (Step 2)
**POST** `/auth/register/doctor/verify-otp/`

**Request:**
```json
{
  "email": "dr.smith@example.com",
  "code": "123456",
  "purpose": "doctor_verification"
}
```

**Response (200):**
```json
{
  "detail": "OTP verified. Your account is pending admin approval."
}
```

---

### 1.6 LOGIN (Email or Username)
**POST** `/auth/login/`

**Request:**
```json
{
  "email_or_username": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "john@example.com",
    "username": "john",
    "role": "PATIENT",
    "phone_number": "+1234567890",
    "is_verified": true,
    "is_active": true,
    "created_at": "2026-05-21T10:00:00Z"
  }
}
```

**Use `role` field to redirect:**
- `role: "PATIENT"` → Redirect to `/dashboard/patient/`
- `role: "DOCTOR"` → Redirect to `/dashboard/doctor/` (only if `is_active=true`)
- `role: "ADMIN"` → Redirect to `/admin/`

---

### 1.7 Google Login
**POST** `/auth/google/`

**Request:**
```json
{
  "access_token": "<google_oauth_token>"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 2,
    "email": "user@gmail.com",
    "username": "user_gmail",
    "role": "PATIENT",
    "is_verified": true,
    "is_active": true
  }
}
```

---

## 2. DASHBOARD ENDPOINTS

### 2.1 Patient Dashboard
**GET** `/dashboard/patient/`  
**Auth Required:** Yes (Patient only)

**Response (200):**
```json
{
  "upcoming_appointments": 3,
  "total_reports": 5,
  "medications_count": 2,
  "unread_notifications": 1
}
```

---

### 2.2 Doctor Dashboard
**GET** `/dashboard/doctor/`  
**Auth Required:** Yes (Doctor only)

**Response (200):**
```json
{
  "total_patients": 12,
  "uploaded_reports": 8,
  "upcoming_appointments": 4,
  "pending_verifications": 2
}
```

---

## 3. PATIENTS ENDPOINTS

### 3.1 Get Patient Profile
**GET** `/patients/me/`  
**Auth Required:** Yes (Patient)

**Response (200):**
```json
{
  "id": 1,
  "user": {
    "email": "john@example.com",
    "username": "john"
  },
  "patient_id": "PAT-2026-0001",
  "full_name": "John Doe",
  "age": 30,
  "gender": "male",
  "address": "123 Main St",
  "emergency_contact": "Jane Doe +0987654321",
  "created_at": "2026-05-21T10:00:00Z"
}
```

---

### 3.2 Update Patient Profile
**PUT** `/patients/me/`  
**Auth Required:** Yes (Patient)

**Request:**
```json
{
  "full_name": "John Doe",
  "age": 31,
  "gender": "male",
  "address": "456 Oak Ave"
}
```

**Response (200):** Updated profile

---

## 4. DOCTORS ENDPOINTS

### 4.1 Get Doctor Profile
**GET** `/doctors/me/`  
**Auth Required:** Yes (Doctor)

**Response (200):**
```json
{
  "id": 1,
  "user": {
    "email": "dr.smith@example.com",
    "username": "dr_smith"
  },
  "full_name": "Dr. Smith",
  "hospital_name": "City Hospital",
  "specialization": "Cardiology",
  "medical_license_number": "MD123456",
  "years_of_experience": 10,
  "verification_status": "approved",
  "verified_at": "2026-05-21T12:00:00Z"
}
```

---

### 4.2 List Pending Doctor Approvals (Admin)
**GET** `/doctors/pending-approvals/`  
**Auth Required:** Yes (Admin only)

**Response (200):**
```json
[
  {
    "id": 2,
    "full_name": "Dr. Johnson",
    "hospital_name": "General Hospital",
    "specialization": "Neurology",
    "verification_status": "pending"
  }
]
```

---

### 4.3 Approve Doctor (Admin)
**POST** `/doctors/approve/<doctor_id>/`  
**Auth Required:** Yes (Admin)

**Request:**
```json
{
  "action": "approve"
}
```

**Response (200):**
```json
{
  "detail": "Doctor approved successfully."
}
```

---

## 5. MEDICAL REPORTS ENDPOINTS

### 5.1 Upload Medical Report (Doctor)
**POST** `/reports/upload/`  
**Auth Required:** Yes (Doctor only)

**Request (form-data):**
```
file: <binary_pdf_or_image>
patient_id: 1
diagnosis: "Hypertension Stage 1"
prescription: "Amlodipine 5mg daily"
```

**Response (201):**
```json
{
  "id": 1,
  "patient": {
    "patient_id": "PAT-2026-0001",
    "full_name": "John Doe"
  },
  "diagnosis": "Hypertension Stage 1",
  "prescription": "Amlodipine 5mg daily",
  "file": "http://127.0.0.1:8000/media/reports/...",
  "uploaded_by": {
    "full_name": "Dr. Smith"
  },
  "created_at": "2026-05-21T10:00:00Z"
}
```

---

### 5.2 List Reports (Patient - Own Reports Only)
**GET** `/reports/`  
**Auth Required:** Yes (Patient)

**Response (200):**
```json
[
  {
    "id": 1,
    "patient": {...},
    "diagnosis": "Hypertension Stage 1",
    "prescription": "Amlodipine 5mg daily",
    "file": "...",
    "uploaded_by": {...},
    "created_at": "2026-05-21T10:00:00Z"
  }
]
```

---

### 5.3 Retrieve Report Detail
**GET** `/reports/<report_id>/`  
**Auth Required:** Yes

**Response (200):** Full report details

---

## 6. APPOINTMENTS ENDPOINTS

### 6.1 Create Appointment (Patient)
**POST** `/appointments/`  
**Auth Required:** Yes (Patient)

**Request:**
```json
{
  "doctor_id": 1,
  "scheduled_at": "2026-06-15T14:30:00Z",
  "reason": "Regular checkup"
}
```

**Response (201):**
```json
{
  "id": 1,
  "patient": {...},
  "doctor": {...},
  "scheduled_at": "2026-06-15T14:30:00Z",
  "reason": "Regular checkup",
  "status": "scheduled",
  "created_at": "2026-05-21T10:00:00Z"
}
```

---

### 6.2 List Appointments (Patient)
**GET** `/appointments/`  
**Auth Required:** Yes (Patient)

**Query Params:**
- `status=scheduled` (filter by status)

**Response (200):**
```json
[
  {
    "id": 1,
    "patient": {...},
    "doctor": {...},
    "scheduled_at": "2026-06-15T14:30:00Z",
    "reason": "Regular checkup",
    "status": "scheduled"
  }
]
```

---

### 6.3 Update Appointment Status (Doctor/Admin)
**PATCH** `/appointments/<appointment_id>/`  
**Auth Required:** Yes

**Request:**
```json
{
  "status": "completed"
}
```

**Response (200):** Updated appointment

---

## 7. NOTIFICATIONS ENDPOINTS

### 7.1 List User Notifications
**GET** `/notifications/`  
**Auth Required:** Yes

**Response (200):**
```json
[
  {
    "id": 1,
    "user": {...},
    "title": "New report uploaded",
    "message": "Dr. Smith uploaded a new medical report for you.",
    "is_read": false,
    "created_at": "2026-05-21T10:00:00Z"
  }
]
```

---

### 7.2 Mark Notification as Read
**PATCH** `/notifications/<notification_id>/mark-read/`  
**Auth Required:** Yes

**Response (200):**
```json
{
  "is_read": true
}
```

---

## 8. ADMIN ENDPOINTS

### 8.1 Django Admin Panel
**GET** `/admin/`  
**Auth Required:** Yes (Superuser/Admin)

**Login:** admin@local / AdminPass123

---

## ERROR RESPONSES

All errors follow this format:

**400 Bad Request:**
```json
{
  "field_name": ["Error message"]
}
```

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```

---

## TESTING FLOW

1. **Register Patient:**
   ```bash
   POST /auth/register/patient/
   ```

2. **Verify OTP:**
   ```bash
   POST /auth/register/patient/verify-otp/
   ```

3. **Set Password:**
   ```bash
   POST /auth/register/patient/password/
   ```
   (Get JWT tokens in response)

4. **Use JWT to Access Dashboard:**
   ```bash
   GET /dashboard/patient/
   Header: Authorization: Bearer <access_token>
   ```

5. **Similar flow for Doctors** (with admin approval required)

---

## JWT TOKEN USAGE

**Access Token:** Valid for 60 minutes (for API requests)
**Refresh Token:** Valid for 1 day (to get new access token)

**To Refresh Access Token:**
```bash
POST /api/token/refresh/
{
  "refresh": "<refresh_token>"
}
```

---

## PASSWORD REQUIREMENTS
- Minimum 8 characters
- 1 uppercase letter
- 1 lowercase letter
- 1 number
- 1 special character
- Cannot contain username or email

---

## ROLE-BASED ACCESS CONTROL

| Endpoint | Patient | Doctor | Admin |
|----------|---------|--------|-------|
| `/dashboard/patient/` | ✓ | ✗ | ✗ |
| `/dashboard/doctor/` | ✗ | ✓ | ✓ |
| `/reports/` (list own) | ✓ | ✓ | ✓ |
| `/reports/upload/` | ✗ | ✓ | ✗ |
| `/appointments/` | ✓ | ✓ | ✓ |
| `/doctors/approve/` | ✗ | ✗ | ✓ |

