from django.conf import settings
from django.db import models


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='appointments')
    booked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_at = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f'Appointment {self.patient.patient_id} with {self.doctor.full_name} at {self.scheduled_at}'
