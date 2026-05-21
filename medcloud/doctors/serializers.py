from rest_framework import serializers
from .models import DoctorProfile


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = ['id', 'full_name', 'hospital_name', 'specialization', 'medical_license_number', 'years_of_experience', 'hospital_email_domain', 'verification_status', 'is_doctor_verified', 'created_at']
        read_only_fields = ['id', 'verification_status', 'is_doctor_verified', 'created_at']


class DoctorVerificationSerializer(serializers.Serializer):
    verification_status = serializers.ChoiceField(choices=DoctorProfile.VERIFICATION_STATUS_CHOICES)
