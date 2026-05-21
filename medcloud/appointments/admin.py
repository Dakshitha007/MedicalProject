from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'scheduled_at', 'status', 'booked_by']
    list_filter = ['status', 'scheduled_at']
    search_fields = ['patient__patient_id', 'doctor__full_name', 'booked_by__email']
