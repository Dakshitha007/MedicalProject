from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import LoginHistory, OTPVerification, User
from .utils import generate_secure_otp, send_otp_email, send_sms_otp


def create_login_history(identifier, user=None, successful=False, request=None, note=None):
    ip = None
    user_agent = None
    if request is not None:
        ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    return LoginHistory.objects.create(
        user=user,
        login_identifier=identifier,
        successful=successful,
        ip_address=ip,
        user_agent=user_agent,
        note=note,
    )


def build_jwt_tokens(user):
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    return {
        'refresh': str(refresh),
        'access': str(access_token),
        'user': {
            'id': str(user.id),
            'email': user.email,
            'username': user.username,
            'role': user.role,
            'is_verified': user.is_verified,
        },
    }


def ensure_patient_profile_id(user):
    if user.role != User.ROLE_PATIENT:
        return
    from patients.models import PatientProfile

    profile, _ = PatientProfile.objects.get_or_create(user=user)
    if not profile.patient_id:
        profile.save()


def send_registration_otp(user, purpose='registration', channel='email'):
    ensure_patient_profile_id(user)

    if channel == 'sms' and user.phone_number:
        otp_record = OTPVerification.create_otp(user=user, phone_number=user.phone_number, purpose=purpose, sent_via='sms')
        try:
            send_sms_otp(user.phone_number, otp_record.code)
        except Exception as exc:
            print(f'OTP SMS send failed: {exc}')
        return otp_record

    otp_record = OTPVerification.create_otp(user=user, email=user.email, purpose=purpose, sent_via='email')
    try:
        send_otp_email(user.email, otp_record.code, purpose=purpose)
    except Exception as exc:
        print(f'OTP email send failed: {exc}')
        if settings.DEBUG:
            print(f'DEBUG OTP for {user.email}: {otp_record.code}')
    return otp_record


def verify_otp_code(email=None, phone_number=None, code=None, purpose=OTPVerification.PURPOSE_REGISTRATION):
    if not email and not phone_number:
        return None, 'Email or phone number is required to verify OTP.'

    query = OTPVerification.objects.filter(purpose=purpose, is_verified=False)
    if email:
        query = query.filter(email__iexact=email)
    if phone_number:
        query = query.filter(phone_number=phone_number)
    otp = query.order_by('-created_at').first()
    if otp is None:
        return None, 'No OTP was requested for this email or phone number. Please register again with the correct contact details.'
    if otp.is_expired():
        return None, 'OTP has expired. Request a new code.'
    if otp.attempts >= 5:
        return None, 'Maximum OTP retry attempts exceeded.'
    otp.attempts += 1
    otp.save(update_fields=['attempts'])
    if otp.code != code:
        return None, 'OTP code is invalid.'
    otp.mark_verified()
    return otp, None


def generate_unique_patient_id():
    from patients.models import PatientProfile
    patient_id = None
    while not patient_id:
        candidate = f'PAT-{timezone.now().year}-{secrets.randbelow(9000) + 1000}'
        if not PatientProfile.objects.filter(patient_id=candidate).exists():
            patient_id = candidate
    return patient_id
