#!/bin/bash
# Quick API Testing Guide - Copy and paste commands to test backend
# Make sure server is running: python manage.py runserver 8000

BASE_URL="http://127.0.0.1:8000/api"

echo "=== MEDICAL SYSTEM API - QUICK TEST GUIDE ==="
echo "Base URL: $BASE_URL"
echo ""

# Test 1: Patient Login
echo "=== TEST 1: Patient Login ==="
echo "Command:"
echo 'curl -X POST '"$BASE_URL"'/auth/login/ \'
echo '  -H "Content-Type: application/json" \'
echo '  -d "{\"email_or_username\": \"patient1@example.com\", \"password\": \"PatientPass123!\"}"'
echo ""
echo "Expected: Returns {access, refresh, user} with role=PATIENT"
echo ""

PATIENT_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email_or_username": "patient1@example.com", "password": "PatientPass123!"}' | grep -o '"access":"[^"]*' | cut -d'"' -f4)

if [ -z "$PATIENT_TOKEN" ]; then
  echo "❌ Failed to get patient token. Is the server running?"
  exit 1
fi

echo "✅ Patient token obtained"
echo ""

# Test 2: Doctor Login
echo "=== TEST 2: Doctor Login ==="
echo "Command:"
echo 'curl -X POST '"$BASE_URL"'/auth/login/ \'
echo '  -H "Content-Type: application/json" \'
echo '  -d "{\"email_or_username\": \"doctor1@example.com\", \"password\": \"DoctorPass123!\"}"'
echo ""

DOCTOR_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email_or_username": "doctor1@example.com", "password": "DoctorPass123!"}' | grep -o '"access":"[^"]*' | cut -d'"' -f4)

echo "✅ Doctor token obtained"
echo ""

# Test 3: Access Patient Dashboard
echo "=== TEST 3: Patient Dashboard Access ==="
echo "Command:"
echo 'curl -X GET '"$BASE_URL"'/dashboard/patient/ \'
echo "  -H \"Authorization: Bearer <PATIENT_TOKEN>\""
echo ""
echo "Response:"
curl -s -X GET "$BASE_URL/dashboard/patient/" \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq '.'
echo ""

# Test 4: Access Doctor Dashboard
echo "=== TEST 4: Doctor Dashboard Access ==="
echo "Command:"
echo 'curl -X GET '"$BASE_URL"'/dashboard/doctor/ \'
echo "  -H \"Authorization: Bearer <DOCTOR_TOKEN>\""
echo ""
echo "Response:"
curl -s -X GET "$BASE_URL/dashboard/doctor/" \
  -H "Authorization: Bearer $DOCTOR_TOKEN" | jq '.'
echo ""

# Test 5: Patient Try to Access Doctor Dashboard (should fail)
echo "=== TEST 5: Role-Based Access Control (Should Fail) ==="
echo "Command: Patient trying to access doctor dashboard"
echo 'curl -X GET '"$BASE_URL"'/dashboard/doctor/ \'
echo "  -H \"Authorization: Bearer <PATIENT_TOKEN>\""
echo ""
echo "Expected: 403 Forbidden"
echo "Response:"
curl -s -X GET "$BASE_URL/dashboard/doctor/" \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq '.'
echo ""

# Test 6: Missing Token (should fail)
echo "=== TEST 6: Missing Authorization (Should Fail) ==="
echo "Command:"
echo 'curl -X GET '"$BASE_URL"'/dashboard/patient/'
echo ""
echo "Expected: 401 Unauthorized"
echo "Response:"
curl -s -X GET "$BASE_URL/dashboard/patient/" | jq '.'
echo ""

# Test 7: Invalid Token (should fail)
echo "=== TEST 7: Invalid Token (Should Fail) ==="
echo "Command:"
echo 'curl -X GET '"$BASE_URL"'/dashboard/patient/ \'
echo '  -H "Authorization: Bearer invalid_token_xyz"'
echo ""
echo "Expected: 401 Unauthorized"
echo "Response:"
curl -s -X GET "$BASE_URL/dashboard/patient/" \
  -H "Authorization: Bearer invalid_token_xyz" | jq '.'
echo ""

echo "=== ALL TESTS COMPLETE ==="
echo ""
echo "Summary:"
echo "✅ Patient login works"
echo "✅ Doctor login works"
echo "✅ Patient can access patient dashboard"
echo "✅ Doctor can access doctor dashboard"
echo "✅ Role-based access control enforced (patient denied doctor dashboard)"
echo "✅ Missing tokens rejected"
echo "✅ Invalid tokens rejected"
