from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from authentication.permissions import IsDoctor, IsPatient, IsDoctorVerified
from .models import MedicalReport
from .serializers import MedicalReportSerializer
from patients.models import PatientProfile


class MedicalReportViewSet(viewsets.ModelViewSet):
    queryset = MedicalReport.objects.select_related('patient', 'uploaded_by').all()
    serializer_class = MedicalReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'DOCTOR':
            return self.queryset.filter(uploaded_by=user)
        if user.role == 'PATIENT':
            patient_profile = get_object_or_404(PatientProfile, user=user)
            return self.queryset.filter(patient=patient_profile)
        return self.queryset.none()

    def get_permissions(self):
        if self.action == 'create':
            return [permission() for permission in [IsAuthenticated, IsDoctorVerified]]
        return [permission() for permission in [IsAuthenticated]]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def create(self, request, *args, **kwargs):
        patient_id = request.data.get('patient_id')
        patient = get_object_or_404(PatientProfile, patient_id=patient_id)
        serializer = self.get_serializer(data={**request.data, 'patient_id': patient.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
