import re
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, role='PATIENT', **extra_fields):
        if not email:
            raise ValueError('Users must have an email address.')
        if not username:
            raise ValueError('Users must have a username.')
        email = self.normalize_email(email.strip())
        username = username.strip()
        user = self.model(email=email, username=username, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email=email, username=username, password=password, role='ADMIN', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_PATIENT = 'PATIENT'
    ROLE_DOCTOR = 'DOCTOR'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = [
        (ROLE_PATIENT, 'Patient'),
        (ROLE_DOCTOR, 'Doctor'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    phone_number = models.CharField(max_length=32, blank=True, validators=[RegexValidator(regex=r'^\+?\d{7,15}$', message='Enter a valid phone number.')])
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_patient(self):
        return self.role == self.ROLE_PATIENT

    @property
    def is_doctor(self):
        return self.role == self.ROLE_DOCTOR

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser


class OTPVerification(models.Model):
    PURPOSE_REGISTRATION = 'registration'
    PURPOSE_PASSWORD_RESET = 'password_reset'
    PURPOSE_DOCTOR_CONFIRM = 'doctor_verification'
    PURPOSE_GOOGLE_LOGIN = 'google_login'
    PURPOSE_CHOICES = [
        (PURPOSE_REGISTRATION, 'Registration'),
        (PURPOSE_PASSWORD_RESET, 'Password reset'),
        (PURPOSE_DOCTOR_CONFIRM, 'Doctor verification'),
        (PURPOSE_GOOGLE_LOGIN, 'Google login'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=32, blank=True, null=True)
    code = models.CharField(max_length=8)
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES, default=PURPOSE_REGISTRATION)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    sent_via = models.CharField(max_length=20, choices=[('email', 'Email'), ('sms', 'SMS')], default='email')

    class Meta:
        indexes = [models.Index(fields=['email', 'phone_number', 'purpose', 'is_verified'])]

    def __str__(self):
        return f'{self.purpose} OTP for {self.email or self.phone_number}'

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_verified(self):
        self.is_verified = True
        self.save(update_fields=['is_verified'])

    @staticmethod
    def create_otp(email=None, phone_number=None, purpose=PURPOSE_REGISTRATION, sent_via='email', user=None):
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        now = timezone.now()
        expires = now + timedelta(minutes=5)
        return OTPVerification.objects.create(
            user=user,
            email=email,
            phone_number=phone_number,
            code=code,
            purpose=purpose,
            expires_at=expires,
            sent_via=sent_via,
        )


class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    login_identifier = models.CharField(max_length=255)
    successful = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status_text = 'SUCCESS' if self.successful else 'FAILURE'
        return f'Login attempt for {self.login_identifier} - {status_text}'
