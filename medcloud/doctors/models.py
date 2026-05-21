from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class DoctorProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctorprofile')
    full_name = models.CharField(max_length=256)
    hospital_name = models.CharField(max_length=256)
    specialization = models.CharField(max_length=128)
    medical_license_number = models.CharField(max_length=32, validators=[RegexValidator(regex=r'^[A-Z0-9\-]{6,24}$', message='Enter a valid license number.')])
    years_of_experience = models.PositiveIntegerField(default=0)
    hospital_email_domain = models.CharField(max_length=128, blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    is_doctor_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.user.email})'
