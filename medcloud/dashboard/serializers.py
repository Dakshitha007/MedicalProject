from rest_framework import serializers


class PatientDashboardSerializer(serializers.Serializer):
    upcoming_appointments = serializers.IntegerField()
    total_reports = serializers.IntegerField()
    medications_count = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()


class DoctorDashboardSerializer(serializers.Serializer):
    total_patients = serializers.IntegerField()
    uploaded_reports = serializers.IntegerField()
    upcoming_appointments = serializers.IntegerField()
    pending_verifications = serializers.IntegerField()
