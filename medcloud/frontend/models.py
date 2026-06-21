import hashlib
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from blockchain.blockchain_service import add_consent_hash


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
    mfa_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=64, blank=True, null=True)

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
    report = models.ForeignKey(MedicalReport, on_delete=models.CASCADE, related_name='blockchain_records', blank=True, null=True)
    report_hash = models.CharField(max_length=128, db_index=True, blank=True, null=True)
    transaction_reference = models.CharField(max_length=256, blank=True, null=True)
    block_timestamp = models.DateTimeField(blank=True, null=True)
    verification_status = models.CharField(max_length=32, default='pending')
    consent = models.ForeignKey('Consent', on_delete=models.CASCADE, related_name='blockchain_records', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.consent_id:
            return f"ConsentBlockchainRecord: {self.consent_id} @ {self.block_timestamp or 'unknown'}"
        return f"BlockchainRecord: {self.report_id} @ {self.block_timestamp or 'unknown'}"


class Consent(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consents')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='granted_consents')
    scope = models.CharField(max_length=128)
    purpose = models.TextField()
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    revoked = models.BooleanField(default=False)
    signature_hash = models.CharField(max_length=128, blank=True)

    def is_active(self):
        if self.revoked:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    consent_txid = models.CharField(max_length=128, blank=True, null=True)
    consent_block_number = models.PositiveIntegerField(blank=True, null=True)

    def _compute_signature_hash(self):
        parts = [
            str(self.patient_id),
            str(self.doctor_id),
            self.scope,
            self.purpose,
            self.granted_at.isoformat() if self.granted_at else '',
            self.expires_at.isoformat() if self.expires_at else '',
            str(self.revoked),
        ]
        return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()

    def save(self, *args, **kwargs):
        new_record = self.pk is None
        with transaction.atomic():
            super().save(*args, **kwargs)
            signature = self._compute_signature_hash()
            if self.signature_hash != signature or new_record:
                self.signature_hash = signature
                try:
                    txid_data = add_consent_hash(
                        consent_id=self.id,
                        patient_id=self.patient_id,
                        doctor_id=self.doctor_id,
                        scope=self.scope,
                        purpose=self.purpose,
                        granted_at=self.granted_at,
                        expires_at=self.expires_at,
                        revoked=self.revoked,
                        signature_hash=self.signature_hash,
                    )
                except Exception:
                    # Ensure we do not leave a consent record with an unanchored blockchain entry.
                    if new_record and self.pk:
                        self.delete()
                    raise
                self.consent_txid = txid_data['txid']
                self.consent_block_number = txid_data['block_number']
                super().save(update_fields=['signature_hash', 'consent_txid', 'consent_block_number'])

    def __str__(self):
        return f"Consent: {self.patient} -> {self.doctor} ({self.scope})"


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
