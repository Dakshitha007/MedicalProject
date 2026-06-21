from pathlib import Path

from rest_framework import serializers
from .models import PatientProfile, Appointment, Medication, Report


ALLOWED_UPLOAD_EXTENSIONS = {
    '.pdf': b'%PDF-',
    '.png': b'\x89PNG\r\n\x1a\n',
    '.jpg': b'\xff\xd8\xff',
    '.jpeg': b'\xff\xd8\xff',
}


def _is_valid_magic_bytes(header: bytes, extension: str) -> bool:
    expected = ALLOWED_UPLOAD_EXTENSIONS.get(extension)
    if not expected:
        return False
    return header.startswith(expected)


class PatientProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PatientProfile
        fields = ['id', 'user', 'full_name', 'date_of_birth', 'gender', 'phone']
        read_only_fields = ['user']


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_id', 'scheduled_at', 'reason', 'status']

    def update(self, instance, validated_data):
        validated_data.pop('patient', None)
        return super().update(instance, validated_data)


class MedicationSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = Medication
        fields = ['id', 'patient', 'patient_id', 'name', 'dosage', 'frequency', 'start_date', 'end_date']

    def update(self, instance, validated_data):
        validated_data.pop('patient', None)
        return super().update(instance, validated_data)


class ReportSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), write_only=True, source='patient')

    class Meta:
        model = Report
        fields = ['id', 'patient', 'patient_id', 'title', 'file', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def validate_file(self, value):
        if value is None:
            raise serializers.ValidationError('No file uploaded.')

        max_size = 10 * 1024 * 1024
        if getattr(value, 'size', None) is not None and value.size > max_size:
            raise serializers.ValidationError('File is too large (max 10MB).')

        filename = getattr(value, 'name', '')
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            raise serializers.ValidationError('Unsupported file extension. Allowed: PDF, PNG, JPG, JPEG.')

        try:
            header = value.read(16)
            value.seek(0)
        except Exception:
            raise serializers.ValidationError('Unable to read uploaded file.')

        if not _is_valid_magic_bytes(header, extension):
            raise serializers.ValidationError('File content does not match its declared type.')

        return value

    def update(self, instance, validated_data):
        validated_data.pop('patient', None)
        validated_data.pop('file', None)
        return super().update(instance, validated_data)
