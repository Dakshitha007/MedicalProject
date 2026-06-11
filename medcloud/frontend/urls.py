from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('login/', views.login_view, name='login-page'),
    path('google-login/<str:role>/', views.google_login, name='google-login-role'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_choice, name='register-choice'),
    path('register/patient/', views.register_patient, name='register-patient'),
    path('register/patient/verify/', views.register_patient_verify, name='register-patient-verify'),
    path('register/doctor/', views.register_doctor, name='register-doctor'),
    path('register/doctor/verify/', views.register_doctor_verify, name='register-doctor-verify'),
    path('register/password/', views.register_password_set, name='register-password'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/patient/', views.patient_dashboard, name='patient-dashboard-ui'),
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor-dashboard-ui'),
    path('upload/', views.upload, name='upload'),
    path('reports/', views.reports, name='reports'),
]