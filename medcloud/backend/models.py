from django.db import models
from django.conf import settings


class PatientProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
	full_name = models.CharField(max_length=200)
	date_of_birth = models.DateField(null=True, blank=True)
	gender = models.CharField(max_length=20, blank=True)
	phone = models.CharField(max_length=30, blank=True)

	def __str__(self):
		return self.full_name


class Appointment(models.Model):
	STATUS_CHOICES = [
		('scheduled', 'Scheduled'),
		('completed', 'Completed'),
		('cancelled', 'Cancelled'),
	]
	patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
	scheduled_at = models.DateTimeField()
	reason = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

	def __str__(self):
		return f"{self.patient} @ {self.scheduled_at}"


class Medication(models.Model):
	patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
	name = models.CharField(max_length=200)
	dosage = models.CharField(max_length=100, blank=True)
	frequency = models.CharField(max_length=100, blank=True)
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)

	def __str__(self):
		return f"{self.name} for {self.patient}"


class Report(models.Model):
	patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
	title = models.CharField(max_length=255)
	file = models.FileField(upload_to='reports/')
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.title
