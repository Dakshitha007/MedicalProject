from django.urls import path
from .views import DoctorDashboardView, PatientDashboardView

urlpatterns = [
    path('patient/', PatientDashboardView.as_view(), name='api-patient-dashboard'),
    path('doctor/', DoctorDashboardView.as_view(), name='api-doctor-dashboard'),
]
