from django.contrib import admin
from .models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'patient_id', 'age', 'gender', 'user']
    search_fields = ['full_name', 'patient_id', 'user__email']
