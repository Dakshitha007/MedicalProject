from django.contrib import admin
from .models import PatientProfile, Appointment, Medication, Report


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
	list_display = ('full_name', 'phone', 'date_of_birth')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
	list_display = ('patient', 'scheduled_at', 'status')
	list_filter = ('status',)


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
	list_display = ('name', 'patient', 'dosage')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
	list_display = ('title', 'patient', 'uploaded_at')
