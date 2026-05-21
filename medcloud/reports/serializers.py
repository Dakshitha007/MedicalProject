from rest_framework import serializers
from .models import MedicalReport
from patients.models import PatientProfile
from patients.serializers import PatientProfileSerializer


class MedicalReportSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = MedicalReport
        fields = ['id', 'uploaded_by', 'patient', 'patient_id', 'diagnosis', 'prescription', 'file', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'patient', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient_id'].queryset = self.Meta.model._meta.get_field('patient').related_model.objects.all()

    def validate_file(self, value):
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError('Upload must not exceed 10MB.')
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError('Unsupported file type.')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['uploaded_by'] = request.user
        return super().create(validated_data)
