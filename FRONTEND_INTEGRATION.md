# Frontend Integration Guide - Medical System

## Overview
The frontend is now fully integrated with the backend Django REST API. Users can log in with credentials, and the system will authenticate via JWT tokens and route them to role-specific dashboards.

## What's Changed

### ✅ Login Page Integration
- **File:** `frontend/templates/login.html`
- **Change:** Login form now calls `POST /api/auth/login/`
- **Behavior:** 
  - Validates email format
  - Sends credentials to backend
  - Receives JWT tokens + user role
  - Stores tokens in localStorage
  - Redirects based on role (PATIENT → patient dashboard, DOCTOR → doctor dashboard)

### ✅ Role-Based Dashboards
- **Patient Dashboard:** `frontend/templates/patient-dashboard.html`
  - Shows: Upcoming appointments, medical reports, medications, notifications
  - Restricted to PATIENT role only
  - Fetches data from `GET /api/dashboard/patient/`
  
- **Doctor Dashboard:** `frontend/templates/doctor-dashboard.html`
  - Shows: Total patients, reports uploaded, upcoming appointments, pending approvals
  - Restricted to DOCTOR role only
  - Fetches data from `GET /api/dashboard/doctor/`

### ✅ API Utilities
- **File:** `frontend/templates/api-utils.js`
- **Contains:**
  - `apiCall()` - Make authenticated API requests
  - `isAuthenticated()` - Check if user is logged in
  - `requireRole()` - Enforce role-based access
  - `refreshToken()` - Auto-refresh expired tokens
  - `logout()` - Clear session and redirect to login

### ✅ Updated Views
- **File:** `frontend/views.py`
- **Added:**
  - `patient_dashboard()` - Render patient dashboard
  - `doctor_dashboard()` - Render doctor dashboard
  - CSRF token generation for frontend

### ✅ Updated URLs
- **File:** `frontend/urls.py`
- **New Routes:**
  - `/dashboard/patient/` → Patient dashboard
  - `/dashboard/doctor/` → Doctor dashboard

## How It Works

### 1. User Logs In

```javascript
// User enters email and password in login form
// Form POSTs to /api/auth/login/
{
  email_or_username: "patient1@example.com",
  password: "PatientPass123!"
}

// Backend returns:
{
  access: "eyJ0eXAiOiJKV1QiLCJhbGc...",
  refresh: "eyJ0eXAiOiJKV1QiLCJhbGc...",
  user: {
    id: 2,
    email: "patient1@example.com",
    role: "PATIENT",
    is_verified: true
  }
}
```

### 2. Frontend Stores Tokens

```javascript
localStorage.setItem('access_token', data.access);
localStorage.setItem('refresh_token', data.refresh);
localStorage.setItem('user_role', data.user.role);
localStorage.setItem('user_id', data.user.id);
localStorage.setItem('user_email', data.user.email);
```

### 3. Frontend Redirects by Role

```javascript
if (role === 'PATIENT') {
  window.location.href = '/dashboard/patient/';
} else if (role === 'DOCTOR') {
  window.location.href = '/dashboard/doctor/';
} else if (role === 'ADMIN') {
  window.location.href = '/admin/';
}
```

### 4. Dashboard Fetches Data

```javascript
// Patient dashboard calls:
const dashboardData = await apiCall('/dashboard/patient/');
// Returns:
{
  upcoming_appointments: 2,
  total_reports: 5,
  medications_count: 3,
  unread_notifications: 1
}

// Doctor dashboard calls:
const dashboardData = await apiCall('/dashboard/doctor/');
// Returns:
{
  total_patients: 12,
  uploaded_reports: 8,
  upcoming_appointments: 4,
  pending_verifications: 1
}
```

### 5. API Calls Include JWT Token

```javascript
// Every API call includes Authorization header
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...',
  'X-CSRFToken': 'csrf-token-value'
}
```

### 6. Token Refresh (Automatic)

```javascript
// If token expires (401 response):
// 1. Frontend calls /api/auth/token/refresh/
// 2. Gets new access token
// 3. Retries original request
// 4. All transparent to user

// If refresh fails:
// 1. Clear localStorage
// 2. Redirect to login
```

## Testing the Integration

### Prerequisites
1. Backend running: `python manage.py runserver 8000`
2. Fresh db with seed data: `python manage.py seed_test_data`

### Test Flow: Patient Login

**Step 1:** Navigate to login page
```
http://127.0.0.1:8000/
```

**Step 2:** Enter patient credentials
```
Email: patient1@example.com
Password: PatientPass123!
```

**Step 3:** Verify redirect
```
Should redirect to: /dashboard/patient/
Should show: Patient-specific metrics
- Upcoming Appointments
- Medical Reports
- Active Medications
- Unread Messages
```

**Step 4:** Verify dashboard data loads
```
Should show dashboard metrics from /api/dashboard/patient/
```

**Step 5:** Verify logout
```
Click "Sign Out" button
Should redirect to login page
localStorage should be cleared
```

### Test Flow: Doctor Login

**Step 1:** Navigate to login page
```
http://127.0.0.1:8000/
```

**Step 2:** Enter doctor credentials
```
Email: doctor1@example.com
Password: DoctorPass123!
```

**Step 3:** Verify redirect
```
Should redirect to: /dashboard/doctor/
Should show: Doctor-specific metrics
- Total Patients
- Reports Uploaded
- Upcoming Appointments
- Pending Approvals
```

**Step 4:** Verify dashboard data loads
```
Should show dashboard metrics from /api/dashboard/doctor/
```

### Test Flow: Role-Based Access Control

**Step 1:** Login as patient
```
Visit: http://127.0.0.1:8000/dashboard/patient/
Works ✅
```

**Step 2:** Try to access doctor dashboard as patient
```
Visit: http://127.0.0.1:8000/dashboard/doctor/
Should show: "Access denied" alert
Should redirect to login
```

**Step 3:** Login as doctor
```
Visit: http://127.0.0.1:8000/dashboard/doctor/
Works ✅
```

**Step 4:** Try to access patient dashboard as doctor
```
Visit: http://127.0.0.1:8000/dashboard/patient/
Should show: "Access denied" alert
Should redirect to login
```

### Browser Developer Console Tests

**In Firefox/Chrome DevTools Console:**

```javascript
// Check if tokens are stored
localStorage.getItem('access_token');
// Should show: "eyJ0eXAiOiJKV1QiLCJhbGc..."

// Check user info
localStorage.getItem('user_role');
// Should show: "PATIENT" or "DOCTOR"

// Test API call
await apiCall('/dashboard/patient/')
// Should show dashboard metrics

// Verify requireRole works
requireRole('PATIENT');
// Should return: true (if logged in as PATIENT)

requireRole('DOCTOR');
// Should show alert and redirect (if logged in as PATIENT)
```

## Common Issues & Solutions

### Issue 1: Login fails with "Connection error"
**Cause:** Backend server not running
**Solution:** 
```bash
cd medcloud
python manage.py runserver 8000
```

### Issue 2: Login succeeds but dashboard doesn't load
**Cause:** CORS issue or backend data endpoint problem
**Solution:** 
1. Check browser console for errors
2. Verify backend is accessible: `curl http://127.0.0.1:8000/api/dashboard/patient/`
3. Check authentication header is being sent
4. Verify token is valid: `python manage.py shell` → check User model

### Issue 3: "Invalid token" error after login
**Cause:** Token format issue or backend validation problem
**Solution:**
1. Check token is being passed correctly in Authorization header
2. Verify JWT settings in backend (`SIMPLE_JWT`)
3. Check token hasn't expired
4. Refresh token by reloading page

### Issue 4: Logout doesn't clear localStorage
**Cause:** logout() function not being called
**Solution:**
1. Verify logout button calls `onclick="logout()"`
2. Check api-utils.js is loaded
3. Verify localStorage.clear() isn't throwing error

### Issue 5: Can access doctor dashboard as patient
**Cause:** requireRole() not working or role not stored
**Solution:**
1. Check `user_role` in localStorage
2. Verify `requireRole()` is called on page load
3. Check backend is returning correct role in login response

## Files Modified

```
frontend/
├── templates/
│   ├── login.html                  [MODIFIED] - API integration
│   ├── patient-dashboard.html      [NEW] - Patient role dashboard
│   ├── doctor-dashboard.html       [NEW] - Doctor role dashboard
│   ├── api-utils.js                [NEW] - Shared API utilities
│   └── ... (other existing files)
├── views.py                        [MODIFIED] - Added role dashboards
├── urls.py                         [MODIFIED] - Added new routes
└── ... (other files unchanged)
```

## Environment Variables

No new environment variables needed. Frontend uses:
- **API_BASE:** `/api` (hardcoded, proxied through Django)
- **CSRF Token:** Automatically extracted from cookies

## Security Notes

✅ **JWT Tokens:** 
- 60-minute access token
- 1-day refresh token
- Stored in localStorage (sufficient for development)
- For production: consider httpOnly cookies

✅ **CSRF Protection:**
- CSRF token extracted from cookies
- Included in all POST requests
- Configured in Django settings

✅ **Role-Based Access:**
- Enforced on frontend (requireRole checks)
- Enforced on backend (API permissions)
- Double protection prevents unauthorized access

✅ **Token Refresh:**
- Automatic on 401 response
- Prevents accidental logouts on token expiry
- Refresh token validated on backend

## Next Steps

### Phase 2: Enhanced Features
1. **Report Upload** - Wire `/upload/` to `/api/reports/POST`
2. **Report Viewing** - Wire `/reports/` to `/api/reports/GET`
3. **Appointment Creation** - Add UI for booking appointments
4. **Notification System** - Real-time notifications via WebSocket
5. **User Profile Management** - Edit personal information

### Phase 3: Production Ready
1. **Error Handling** - Comprehensive error boundaries
2. **Loading States** - Better UX for slow connections
3. **Pagination** - Handle large datasets
4. **Search/Filter** - Advanced data filtering
5. **Mobile Optimization** - Responsive design enhancements

## Support

### Quick Verification Checklist
- [ ] Backend running on port 8000
- [ ] Login page loads without errors
- [ ] Can login with test credentials
- [ ] Redirects to correct dashboard
- [ ] Dashboard displays metrics
- [ ] Logout clears session
- [ ] Can't access other role's dashboard
- [ ] Browser console has no errors

### Debug Mode
To enable verbose logging:

```javascript
// In browser console:
localStorage.setItem('debug_api', 'true');

// Then modify api-utils.js to log all calls:
console.log('API Call:', method, endpoint, response);
```

---

**Status:** ✅ Frontend fully integrated with backend  
**Last Updated:** 2026-05-21  
**Version:** 1.0
