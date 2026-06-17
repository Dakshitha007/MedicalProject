from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Administrator'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    assigned_patients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='assigned_doctors',
    )

    def __str__(self):
        return f"Profile: {self.user.get_full_name() or self.user.username}"

    @property
    def is_patient(self):
        return self.role == 'patient'

    @property
    def is_doctor(self):
        return self.role == 'doctor'

    @property
    def is_admin(self):
        return self.role == 'admin'


class MedicalReport(models.Model):
    CATEGORY_CHOICES = [
        ('lab', 'Laboratory'),
        ('cardio', 'Cardiology'),
        ('immun', 'Immunization'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('tampered', 'Tampered'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medical_reports')
    report_name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='other')
    encrypted_file = models.FileField(upload_to='reports/encrypted/')
    original_filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_hash = models.CharField(max_length=64, blank=True, null=True)
    # New field: alternate/expanded hash storage (kept nullable to preserve existing data)
    hash_value = models.CharField(max_length=128, blank=True, null=True)
    blockchain_txid = models.CharField(max_length=128, blank=True, null=True)
    block_number = models.PositiveIntegerField(blank=True, null=True)
    verification_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    encryption_metadata = models.JSONField(blank=True, null=True)
    ai_summary = models.TextField(blank=True, null=True)
    doctor_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.report_name} ({self.owner})"


class BlockchainRecord(models.Model):
    report = models.ForeignKey(MedicalReport, on_delete=models.CASCADE, related_name='blockchain_records')
    report_hash = models.CharField(max_length=128, db_index=True)
    transaction_reference = models.CharField(max_length=256, blank=True, null=True)
    block_timestamp = models.DateTimeField(blank=True, null=True)
    verification_status = models.CharField(max_length=32, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BlockchainRecord: {self.report_id} @ {self.block_timestamp or 'unknown'}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='appointments_as_doctor',
    )
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        doctor_label = self.doctor.get_full_name() if self.doctor else 'Unassigned'
        return f"Appointment: {self.patient} with {doctor_label} on {self.appointment_date}"


class Medication(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medications')
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.medicine_name} for {self.patient}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user}: {self.title}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('secure_download', 'Secure Download'),
        ('verify', 'Verify'),
        ('view_report', 'Report View'),
        ('delete', 'Delete'),
        ('appointment_created', 'Appointment Created'),
        ('appointment_updated', 'Appointment Updated'),
        ('appointment_cancelled', 'Appointment Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    report = models.ForeignKey(MedicalReport, on_delete=models.SET_NULL, blank=True, null=True, related_name='audit_logs')
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"


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
