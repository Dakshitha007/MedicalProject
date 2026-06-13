from django.contrib import admin
from .models import UserProfile, MedicalReport, Appointment, Medication, Subscription


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'phone', 'dob')


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
	list_display = ('report_name', 'patient', 'category', 'upload_date')
	search_fields = ('report_name', 'patient__username', 'patient__email')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
	list_display = ('patient', 'doctor_name', 'appointment_date', 'status')
	list_filter = ('status',)


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
	list_display = ('medicine_name', 'patient', 'start_date', 'end_date')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
	list_display = ('user', 'plan_type', 'start_date', 'expiry_date')
