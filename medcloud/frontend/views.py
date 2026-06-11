import json

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.middleware.csrf import get_token
from authentication.models import User

def landing_view(request):
    """Render landing page"""
    return render(request, 'landing.html')


def login_view(request):
    """Render login page"""
    get_token(request)  # Generate CSRF token for frontend
    return render(request, 'login.html', {
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    })


def google_login(request, role):
    role = role.upper()
    if role not in [User.ROLE_PATIENT, User.ROLE_DOCTOR]:
        return redirect('login-page')

    request.session['google_auth_role'] = role
    request.session.modified = True
    # Ensure post-login redirect goes to UI dashboard (not raw API endpoints).
    # Map role to frontend dashboard path and include as `next` for allauth.
    if role == User.ROLE_PATIENT:
        next_url = '/dashboard/patient/'
    elif role == User.ROLE_DOCTOR:
        next_url = '/dashboard/doctor/'
    else:
        next_url = '/dashboard/'

    # Build provider login URL with explicit `process=login` and `next`.
    provider_url = reverse('google_login')
    return redirect(f"{provider_url}?process=login&next={next_url}")


def get_current_user_context(request):
    if not request.user.is_authenticated:
        return {'current_user_json': json.dumps(None)}
    return {
        'current_user_json': json.dumps({
            'id': request.user.id,
            'email': request.user.email,
            'role': request.user.role,
        })
    }


def logout_view(request):
    logout(request)
    return redirect('login-page')


def register_choice(request):
    """Render role selection page for registration"""
    get_token(request)
    return render(request, 'register_choice.html')


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

@login_required
def patient_dashboard(request):
    if request.user.role != User.ROLE_PATIENT:
        return redirect('dashboard')
    context = get_current_user_context(request)
    return render(request, 'patient-dashboard.html', context)


@login_required
def doctor_dashboard(request):
    if request.user.role != User.ROLE_DOCTOR:
        return redirect('dashboard')
    context = get_current_user_context(request)
    return render(request, 'doctor-dashboard.html', context)

@login_required
def dashboard(request):
    if request.user.role == User.ROLE_PATIENT:
        return redirect('/dashboard/patient/')
    if request.user.role == User.ROLE_DOCTOR:
        return redirect('/dashboard/doctor/')
    if request.user.is_staff:
        return redirect('/admin/')
    return redirect('login-page')

def upload(request):
    """Render upload page"""
    context = get_current_user_context(request)
    return render(request, 'upload.html', context)

def reports(request):
    """Render reports page"""
    context = get_current_user_context(request)
    return render(request, 'reports.html', context)