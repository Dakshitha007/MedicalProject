from django.contrib import admin
from .models import MedicalReport


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'uploaded_by', 'created_at']
    search_fields = ['patient__patient_id', 'patient__full_name', 'uploaded_by__email']
    readonly_fields = ['created_at', 'updated_at']
