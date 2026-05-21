from django.conf import settings
from django.db import models
from django.utils import timezone
from authentication.utils import generate_patient_id


class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patientprofile')
    patient_id = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=256)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=128, blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.patient_id:
            candidate = generate_patient_id()
            while PatientProfile.objects.filter(patient_id=candidate).exists():
                candidate = generate_patient_id()
            self.patient_id = candidate
        super().save(*args, **kwargs)
