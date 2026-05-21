from rest_framework import serializers
from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ['id', 'patient_id', 'full_name', 'age', 'gender', 'address', 'emergency_contact', 'medical_history', 'created_at']
        read_only_fields = ['id', 'patient_id', 'created_at']


class PatientDashboardSerializer(serializers.Serializer):
    total_reports = serializers.IntegerField()
    upcoming_appointments = serializers.IntegerField()
    completed_appointments = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
