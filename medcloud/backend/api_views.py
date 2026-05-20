from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import PatientProfile, Appointment, Medication, Report
from .serializers import (
    PatientProfileSerializer,
    AppointmentSerializer,
    MedicationSerializer,
    ReportSerializer,
)


class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff and getattr(request.user, 'is_doctor', False)


class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and not request.user.is_staff


class PatientViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['full_name', 'date_of_birth']


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('patient').all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['scheduled_at', 'status', 'patient__full_name']


class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.select_related('patient').all()
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['patient__full_name', 'name']


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('patient').all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['patient__full_name', 'title']

    def create(self, request, *args, **kwargs):
        # allow file uploads via API; patient_id expected
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
