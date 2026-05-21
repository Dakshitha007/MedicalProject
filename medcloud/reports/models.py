from django.conf import settings
from django.db import models


def report_upload_path(instance, filename):
    return f'reports/{instance.patient.patient_id}/{filename}'


class MedicalReport(models.Model):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_reports')
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='medical_reports')
    diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    file = models.FileField(upload_to=report_upload_path)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report for {self.patient.patient_id} uploaded by {self.uploaded_by.email}'
