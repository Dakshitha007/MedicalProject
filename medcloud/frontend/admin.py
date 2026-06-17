from django.contrib import admin
from .models import (
    UserProfile,
    MedicalReport,
    BlockchainRecord,
    Appointment,
    Medication,
    Notification,
    AuditLog,
    Subscription,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'dob')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_name',
        'owner',
        'category',
        'upload_date',
        'verification_status',
        'block_number',
    )
    search_fields = ('report_name', 'owner__username', 'owner__email', 'blockchain_txid')
    list_filter = ('category', 'verification_status')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'status')
    list_filter = ('status',)
    search_fields = ('patient__username', 'doctor__username')


@admin.register(BlockchainRecord)
class BlockchainRecordAdmin(admin.ModelAdmin):
    list_display = ('report', 'transaction_reference', 'block_timestamp', 'verification_status')
    search_fields = ('report__report_name', 'transaction_reference')
    list_filter = ('verification_status',)


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('medicine_name', 'patient', 'dosage', 'frequency', 'start_date', 'end_date')
    search_fields = ('medicine_name', 'patient__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('title', 'user__username')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_address', 'report')
    list_filter = ('action',)
    search_fields = ('user__username', 'report__report_name', 'details')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_type', 'start_date', 'expiry_date')
    list_filter = ('plan_type',)
