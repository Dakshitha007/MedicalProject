from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import PatientProfile, Appointment, Medication, Report
from .serializers import (
    PatientProfileSerializer,
    AppointmentSerializer,
    MedicationSerializer,
    ReportSerializer,
)


class IsStaffOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        if hasattr(obj, 'patient'):
            return getattr(obj.patient, 'user', None) == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class PatientViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all().select_related('user')
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrOwner]
    filterset_fields = ['full_name', 'date_of_birth']

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied('Only staff may create patient profiles.')
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            serializer.validated_data.pop('user', None)
        serializer.save()


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('patient__user').all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrOwner]
    filterset_fields = ['scheduled_at', 'status', 'patient__full_name']

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(patient__user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_staff or self.request.user.is_superuser:
            serializer.save()
            return

        patient = getattr(self.request.user, 'patientprofile', None)
        if patient is None:
            patient = PatientProfile.objects.create(
                user=self.request.user,
                full_name=self.request.user.get_full_name() or self.request.user.username,
            )
        serializer.save(patient=patient)


class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.select_related('patient__user').all()
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrOwner]
    filterset_fields = ['patient__full_name', 'name']

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(patient__user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_staff or self.request.user.is_superuser:
            serializer.save()
            return

        patient = getattr(self.request.user, 'patientprofile', None)
        if patient is None:
            patient = PatientProfile.objects.create(
                user=self.request.user,
                full_name=self.request.user.get_full_name() or self.request.user.username,
            )
        serializer.save(patient=patient)


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('patient__user').all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrOwner]
    filterset_fields = ['patient__full_name', 'title']

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(patient__user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_staff or self.request.user.is_superuser:
            serializer.save()
            return

        patient = getattr(self.request.user, 'patientprofile', None)
        if patient is None:
            patient = PatientProfile.objects.create(
                user=self.request.user,
                full_name=self.request.user.get_full_name() or self.request.user.username,
            )
        serializer.save(patient=patient)

    def perform_update(self, serializer):
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            serializer.validated_data.pop('patient', None)
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
