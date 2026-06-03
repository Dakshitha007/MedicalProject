# 🚀 Frontend Integration - Quick Test Guide

## 3 Steps to Test the Integration

### Step 1: Verify Backend is Running
```bash
# In Terminal 1:
cd C:\Users\ASUS\OneDrive\Documents\medicalpro\MedicalProject\medcloud
python manage.py runserver 8000
```

**Expected Output:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### Step 2: Test Patient Login (Browser)
1. Open: `http://127.0.0.1:8000/`
2. Enter:
   - **Email:** `patient1@example.com`
   - **Password:** `PatientPass123!`
3. Click **Sign In**

**Expected Behavior:**
- ✅ "Verifying..." loading state appears
- ✅ Page redirects to `/dashboard/patient/`
- ✅ Dashboard shows metrics:
  - Upcoming Appointments: 1
  - Medical Reports: 1
  - Active Medications: 0
  - Unread Messages: 0
- ✅ Logout button works

### Step 3: Test Doctor Login (Browser)
1. Open: `http://127.0.0.1:8000/` (or click logout first)
2. Enter:
   - **Email:** `doctor1@example.com`
   - **Password:** `DoctorPass123!`
3. Click **Sign In**

**Expected Behavior:**
- ✅ Page redirects to `/dashboard/doctor/`
- ✅ Dashboard shows doctor metrics:
  - Total Patients: 1
  - Reports Uploaded: 1
  - Upcoming Appointments: 1
  - Pending Approvals: 0
- ✅ Different layout than patient dashboard

## Role-Based Access Control Test

### Test 1: Patient Cannot Access Doctor Dashboard
1. Login as patient1@example.com
2. Manually visit: `http://127.0.0.1:8000/dashboard/doctor/`

**Expected:** Alert "Access denied" and redirect to login ✅

### Test 2: Doctor Cannot Access Patient Dashboard
1. Login as doctor1@example.com
2. Manually visit: `http://127.0.0.1:8000/dashboard/patient/`

**Expected:** Alert "Access denied" and redirect to login ✅

## Troubleshooting

### Issue: Login page shows error
```
Error: "Connection error. Please try again."
```
**Solution:** Make sure backend is running
```bash
python manage.py runserver 8000
```

### Issue: Invalid credentials error
```
Error: "Invalid email or password"
```
**Solution:** Check test credentials:
- `patient1@example.com / PatientPass123!`
- `doctor1@example.com / DoctorPass123!`

### Issue: Dashboard won't load after login
```
Error: "Unable to load dashboard"
```
**Solution:** Check browser console (F12) for errors
- Look for CORS errors
- Check network tab for failed requests
- Verify backend is responding to `/api/dashboard/patient/`

### Issue: Logout not working
**Solution:** Check if api-utils.js is loaded:
```javascript
// In browser console:
typeof logout  // Should return: "function"
```

## Browser Console Debugging

Press **F12** (Developer Tools) and try these commands:

```javascript
// Check if logged in
localStorage.getItem('access_token')
// Should show: "eyJ0eXAiOiJKV1QiLCJhbGc..."

// Check user role
localStorage.getItem('user_role')
// Should show: "PATIENT" or "DOCTOR"

// Test API call (should work if logged in)
await apiCall('/dashboard/patient/')

// Check if requireRole works
requireRole('PATIENT')  // Returns true or false
```

## What's Changed

| File | Change | Impact |
|------|--------|--------|
| login.html | Now POSTs to `/api/auth/login/` | Authenticates with backend ✅ |
| patient-dashboard.html | NEW - Role-restricted dashboard | Shows patient metrics ✅ |
| doctor-dashboard.html | NEW - Role-restricted dashboard | Shows doctor metrics ✅ |
| api-utils.js | NEW - Shared utilities | Powers all API calls ✅ |
| views.py | Added patient/doctor dashboard views | Routes requests correctly ✅ |
| urls.py | Added new dashboard routes | Maps `/dashboard/patient/` etc ✅ |

## Test Accounts

```
PATIENT:
  Email: patient1@example.com
  Password: PatientPass123!
  
PATIENT:
  Email: patient2@example.com
  Password: PatientPass123!
  
PATIENT:
  Email: patient3@example.com
  Password: PatientPass123!

DOCTOR:
  Email: doctor1@example.com
  Password: DoctorPass123!

DOCTOR:
  Email: doctor2@example.com
  Password: DoctorPass123!

ADMIN:
  Email: admin@local
  Password: AdminPass123
```

## Success Indicators ✅

- [ ] Backend server starts without errors
- [ ] Login page loads and looks correct
- [ ] Can login with patient credentials
- [ ] Patient dashboard displays metrics
- [ ] Can login with doctor credentials
- [ ] Doctor dashboard displays different metrics
- [ ] Cannot access doctor dashboard as patient (access denied)
- [ ] Cannot access patient dashboard as doctor (access denied)
- [ ] Logout works and clears session
- [ ] Browser console has no CORS errors

## Full Integration Test (Complete Flow)

```bash
# Terminal 1: Start backend
cd medcloud
python manage.py runserver 8000

# Browser: Test complete flow
1. Visit http://127.0.0.1:8000/
2. Login as patient1@example.com / PatientPass123!
3. Verify redirect to /dashboard/patient/
4. Verify metrics load: upcoming_appointments, total_reports, etc
5. Click logout
6. Login as doctor1@example.com / DoctorPass123!
7. Verify redirect to /dashboard/doctor/
8. Verify different metrics: total_patients, uploaded_reports, etc
9. Try to visit /dashboard/patient/ - should deny access
10. Click logout
11. Verify redirected to login

Total Time: ~2 minutes
Expected Result: ALL STEPS WORK ✅
```

---

**Frontend Integration Status:** ✅ COMPLETE  
**Ready for User Testing:** YES  
**Production Ready:** Requires minor enhancements (error handling, loading states)
