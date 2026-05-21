import os
import re
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone


def generate_secure_otp(length=6):
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def generate_patient_id():
    year = timezone.now().year
    suffix = secrets.randbelow(9000) + 1000
    return f'PAT-{year}-{suffix}'


def validate_license_number(license_number):
    if not license_number:
        return False
    return bool(re.fullmatch(r'[A-Z0-9\-]{6,24}', license_number.upper()))


def send_otp_email(email, code, purpose='registration'):
    subject = f'{settings.PROJECT_NAME} {purpose.replace("_", " ").title()} OTP'
    message = render_to_string('authentication/email/otp_email.txt', {'code': code, 'purpose': purpose})
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)


def send_sms_otp(phone_number, code):
    # Placeholder implementation; replace with the SMS provider you prefer.
    print(f'SMS OTP for {phone_number}: {code}')
    return True


def get_email_domain(email):
    if not email or '@' not in email:
        return ''
    return email.split('@')[1].lower()


def get_hospital_domains():
    raw = os.getenv('HOSPITAL_EMAIL_DOMAINS', '')
    return [domain.strip().lower() for domain in raw.split(',') if domain.strip()]
