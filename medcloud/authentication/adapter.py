import secrets
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile


def get_full_name(user):
    name = ' '.join(filter(None, [user.first_name, user.last_name])).strip()
    return name or user.username or ''


def get_email_domain(email):
    if not email or '@' not in email:
        return ''
    return email.split('@', 1)[1].lower()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated:
            return

        email = sociallogin.account.extra_data.get('email') or sociallogin.user.email
        if not email:
            return

        try:
            existing = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            existing = None

        if existing:
            updated_fields = []
            if not existing.is_active:
                existing.is_active = True
                updated_fields.append('is_active')
            if not existing.is_verified:
                existing.is_verified = True
                updated_fields.append('is_verified')
            if updated_fields:
                existing.save(update_fields=updated_fields)
            if not sociallogin.is_existing:
                sociallogin.connect(request, existing)
            request.session.pop('google_auth_role', None)
            return

        role = request.session.get('google_auth_role')
        if role in [User.ROLE_PATIENT, User.ROLE_DOCTOR]:
            sociallogin.user.role = role

    def is_auto_signup_allowed(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email') or sociallogin.user.email
        if not email:
            return False
        return super().is_auto_signup_allowed(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        extra_data = sociallogin.account.extra_data

        email = extra_data.get('email') or user.email
        if email:
            user.email = email.lower()

        if form is not None and form.cleaned_data.get('role'):
            user.role = form.cleaned_data['role']
        else:
            role = request.session.get('google_auth_role')
            if role in [User.ROLE_PATIENT, User.ROLE_DOCTOR]:
                user.role = role

        if not user.username:
            base_username = (user.email or '').split('@')[0] or 'user'
            username = base_username.lower().replace(' ', '_')
            while User.objects.filter(username__iexact=username).exists():
                username = f"{base_username}_{secrets.token_hex(3)}"
            user.username = username

        user.first_name = user.first_name or extra_data.get('given_name', '')
        user.last_name = user.last_name or extra_data.get('family_name', '')
        user.is_active = True
        user.is_verified = True
        user.set_unusable_password()

        user = super().save_user(request, sociallogin, form)
        request.session.pop('google_auth_role', None)

        if user.role == User.ROLE_PATIENT:
            full_name = get_full_name(user)
            if not hasattr(user, 'patientprofile'):
                PatientProfile.objects.create(user=user, full_name=full_name)

        if user.role == User.ROLE_DOCTOR:
            if not hasattr(user, 'doctorprofile'):
                DoctorProfile.objects.create(
                    user=user,
                    full_name=get_full_name(user),
                    hospital_name='Google Sign-In',
                    specialization='General Practice',
                    medical_license_number='GOOGLE-0001',
                    years_of_experience=0,
                    hospital_email_domain=get_email_domain(user.email),
                    verification_status='pending',
                    is_doctor_verified=False,
                )

        return user
