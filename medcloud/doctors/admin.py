from django.contrib import admin
from .models import DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'hospital_name', 'specialization', 'medical_license_number', 'verification_status', 'is_doctor_verified']
    search_fields = ['full_name', 'hospital_name', 'medical_license_number', 'user__email']
    list_filter = ['verification_status', 'is_doctor_verified']
