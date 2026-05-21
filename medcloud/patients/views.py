from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import PatientProfile
from .serializers import PatientDashboardSerializer, PatientProfileSerializer
from authentication.permissions import IsPatient
from reports.models import MedicalReport
from appointments.models import Appointment
from notifications.models import Notification


class PatientProfileViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.select_related('user').all()
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated, IsPatient]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PatientDashboardAPIView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsPatient]

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        patient_profile = get_object_or_404(PatientProfile, user=request.user)
        total_reports = MedicalReport.objects.filter(patient=patient_profile).count()
        upcoming_appointments = Appointment.objects.filter(patient=patient_profile, status='scheduled').count()
        completed_appointments = Appointment.objects.filter(patient=patient_profile, status='completed').count()
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
        serializer = PatientDashboardSerializer({
            'total_reports': total_reports,
            'upcoming_appointments': upcoming_appointments,
            'completed_appointments': completed_appointments,
            'unread_notifications': unread_notifications,
        })
        return Response(serializer.data, status=status.HTTP_200_OK)
