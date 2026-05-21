from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorProfileViewSet, PendingDoctorListAPIView

router = DefaultRouter()
router.register(r'profile', DoctorProfileViewSet, basename='doctor-profile')

urlpatterns = [
    path('', include(router.urls)),
    path('pending/', PendingDoctorListAPIView.as_view({'get': 'list'}), name='pending-doctors'),
    path('pending/<int:pk>/', PendingDoctorListAPIView.as_view({'put': 'update'}), name='doctor-verification-update'),
]
