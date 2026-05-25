from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from authentication.permissions import IsAdminUser, IsDoctor
from .models import DoctorProfile
from .serializers import DoctorProfileSerializer, DoctorVerificationSerializer


class DoctorProfileViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.select_related('user').all()
    serializer_class = DoctorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'DOCTOR':
            return self.queryset.filter(user=self.request.user)
        if self.request.user.role == 'PATIENT':
            return self.queryset.filter(is_doctor_verified=True, verification_status='approved')
        return self.queryset.none()

    def create(self, request, *args, **kwargs):
        if request.user.role != 'DOCTOR':
            return Response({'detail': 'Only doctors may create doctor profiles.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PendingDoctorListAPIView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def list(self, request):
        pending = DoctorProfile.objects.filter(verification_status='pending')
        serializer = DoctorProfileSerializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        profile = get_object_or_404(DoctorProfile, pk=pk)
        serializer = DoctorVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile.verification_status = serializer.validated_data['verification_status']
        profile.is_doctor_verified = profile.verification_status == 'approved'
        profile.save(update_fields=['verification_status', 'is_doctor_verified'])
        if profile.verification_status == 'approved':
            profile.user.is_active = True
            profile.user.save(update_fields=['is_active'])
        return Response(DoctorProfileSerializer(profile).data, status=status.HTTP_200_OK)
