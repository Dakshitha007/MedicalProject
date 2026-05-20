from rest_framework import serializers
from .models import PatientProfile, Appointment, Medication, Report


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ['id', 'user', 'full_name', 'date_of_birth', 'gender', 'phone']


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_id', 'scheduled_at', 'reason', 'status']


class MedicationSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = Medication
        fields = ['id', 'patient', 'patient_id', 'name', 'dosage', 'frequency', 'start_date', 'end_date']


class ReportSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = Report
        fields = ['id', 'patient', 'patient_id', 'title', 'file', 'uploaded_at']
        read_only_fields = ['uploaded_at']
