from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from authentication.permissions import IsDoctor, IsPatient
from .models import Appointment
from .serializers import AppointmentSerializer
from patients.models import PatientProfile
from doctors.models import DoctorProfile


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('patient', 'doctor', 'booked_by').all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'PATIENT':
            patient_profile = get_object_or_404(PatientProfile, user=user)
            return self.queryset.filter(patient=patient_profile)
        if user.role == 'DOCTOR':
            doctor_profile = get_object_or_404(DoctorProfile, user=user)
            return self.queryset.filter(doctor=doctor_profile)
        return self.queryset.none()

    def perform_create(self, serializer):
        serializer.save(booked_by=self.request.user)

    def create(self, request, *args, **kwargs):
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        patient = get_object_or_404(PatientProfile, patient_id=patient_id)
        doctor = get_object_or_404(DoctorProfile, id=doctor_id)
        serializer = self.get_serializer(data={**request.data, 'patient_id': patient.id, 'doctor_id': doctor.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
