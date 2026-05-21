from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientDashboardAPIView, PatientProfileViewSet

router = DefaultRouter()
router.register(r'profile', PatientProfileViewSet, basename='patient-profile')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/metrics/', PatientDashboardAPIView.as_view({'get': 'metrics'}), name='patient-dashboard-metrics'),
]
