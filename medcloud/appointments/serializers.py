from rest_framework import serializers
from .models import Appointment
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from patients.serializers import PatientProfileSerializer
from doctors.serializers import DoctorProfileSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    doctor = DoctorProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')
    doctor_id = serializers.PrimaryKeyRelatedField(queryset=DoctorProfile.objects.all(), write_only=True, source='doctor')

    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'doctor', 'patient_id', 'doctor_id', 'scheduled_at', 'reason', 'status', 'created_at']
        read_only_fields = ['id', 'patient', 'doctor', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient_id'].queryset = self.Meta.model._meta.get_field('patient').related_model.objects.all()
        self.fields['doctor_id'].queryset = self.Meta.model._meta.get_field('doctor').related_model.objects.all()

    def create(self, validated_data):
        validated_data['booked_by'] = self.context['request'].user
        return super().create(validated_data)
