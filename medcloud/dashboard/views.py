from django.shortcuts import get_object_or_404
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from authentication.permissions import IsDoctor, IsPatient
from .serializers import DoctorDashboardSerializer, PatientDashboardSerializer
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from reports.models import MedicalReport
from appointments.models import Appointment
from notifications.models import Notification


class PatientDashboardView(views.APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        profile = get_object_or_404(PatientProfile, user=request.user)
        data = {
            'upcoming_appointments': Appointment.objects.filter(patient=profile, status='scheduled').count(),
            'total_reports': MedicalReport.objects.filter(patient=profile).count(),
            'medications_count': 0,
            'unread_notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
        }
        serializer = PatientDashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DoctorDashboardView(views.APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        profile = get_object_or_404(DoctorProfile, user=request.user)
        data = {
            'total_patients': PatientProfile.objects.filter(appointments__doctor=profile).distinct().count(),
            'uploaded_reports': MedicalReport.objects.filter(uploaded_by=request.user).count(),
            'upcoming_appointments': Appointment.objects.filter(doctor=profile, status='scheduled').count(),
            'pending_verifications': DoctorProfile.objects.filter(verification_status='pending').count(),
        }
        serializer = DoctorDashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
