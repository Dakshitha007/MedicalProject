from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.middleware.csrf import get_token
import json

def login_view(request):
    """Render login page"""
    get_token(request)  # Generate CSRF token for frontend
    return render(request, 'login.html', {
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    })


def register_choice(request):
    """Render role selection page for registration"""
    get_token(request)
    return render(request, 'register_choice.html', {
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    })


def register_patient(request):
    get_token(request)
    return render(request, 'register_patient.html')


def register_patient_verify(request):
    get_token(request)
    return render(request, 'register_patient_verify.html')


def register_doctor(request):
    get_token(request)
    return render(request, 'register_doctor.html')


def register_doctor_verify(request):
    get_token(request)
    return render(request, 'register_doctor_verify.html')


def register_password_set(request):
    get_token(request)
    return render(request, 'register_password_set.html')

def patient_dashboard(request):
    """Render patient dashboard"""
    return render(request, 'patient-dashboard.html')

def doctor_dashboard(request):
    """Render doctor dashboard"""
    return render(request, 'doctor-dashboard.html')

def dashboard(request):
    """Legacy dashboard - redirect based on role"""
    return render(request, 'dashboard.html')

def upload(request):
    """Render upload page"""
    return render(request, 'upload.html')

def reports(request):
    """Render reports page"""
    return render(request, 'reports.html')