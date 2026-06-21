from django.urls import path, include
from rest_framework import routers
from . import views
from . import api_views

router = routers.DefaultRouter()
router.register(r'patients', api_views.PatientViewSet, basename='patient')
router.register(r'appointments', api_views.AppointmentViewSet, basename='appointment')
router.register(r'medications', api_views.MedicationViewSet, basename='medication')
router.register(r'reports', api_views.ReportViewSet, basename='report')

urlpatterns = [
    # legacy simple endpoints
    path('appointments/', views.appointments_list, name='appointments_list'),
    path('appointments/create/', views.appointments_create, name='appointments_create'),
    path('medications/', views.medications_list, name='medications_list'),
    path('medications/create/', views.medications_create, name='medications_create'),
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/upload/', views.upload_report, name='upload_report'),

    # DRF API
    path('v1/', include(router.urls)),
]
