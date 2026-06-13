from django.db import models
from django.conf import settings


class UserProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	phone = models.CharField(max_length=20, blank=True, null=True)
	dob = models.DateField(blank=True, null=True)
	blood_group = models.CharField(max_length=5, blank=True, null=True)
	address = models.TextField(blank=True, null=True)

	def __str__(self):
		return f"Profile: {self.user.get_full_name() or self.user.username}"


class MedicalReport(models.Model):
	CATEGORY_CHOICES = [
		('lab', 'Laboratory'),
		('cardio', 'Cardiology'),
		('immun', 'Immunization'),
		('other', 'Other'),
	]

	patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
	report_name = models.CharField(max_length=255)
	category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='other')
	uploaded_file = models.FileField(upload_to='reports/')
	upload_date = models.DateTimeField(auto_now_add=True)
	ai_summary = models.TextField(blank=True, null=True)
	doctor_notes = models.TextField(blank=True, null=True)

	def __str__(self):
		return f"{self.report_name} ({self.patient})"


class Appointment(models.Model):
	STATUS_CHOICES = [
		('scheduled', 'Scheduled'),
		('completed', 'Completed'),
		('cancelled', 'Cancelled'),
	]

	patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
	doctor_name = models.CharField(max_length=255)
	appointment_date = models.DateTimeField()
	status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='scheduled')

	def __str__(self):
		return f"Appointment: {self.patient} with {self.doctor_name} on {self.appointment_date}"


class Medication(models.Model):
	patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medications')
	medicine_name = models.CharField(max_length=255)
	dosage = models.CharField(max_length=100, blank=True, null=True)
	frequency = models.CharField(max_length=100, blank=True, null=True)
	start_date = models.DateField(blank=True, null=True)
	end_date = models.DateField(blank=True, null=True)

	def __str__(self):
		return f"{self.medicine_name} for {self.patient}"


class Subscription(models.Model):
	PLAN_CHOICES = [
		('free', 'Free'),
		('pro', 'Pro'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
	plan_type = models.CharField(max_length=32, choices=PLAN_CHOICES, default='free')
	start_date = models.DateField(auto_now_add=True)
	expiry_date = models.DateField(blank=True, null=True)

	def __str__(self):
		return f"{self.user} - {self.plan_type}"
