from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    DoctorApprovalAPIView,
    DoctorOTPVerifyAPIView,
    DoctorRegistrationAPIView,
    ResendOTPAPIView,
    GoogleSocialLoginAPIView,
    LoginAPIView,
    PatientOTPVerifyAPIView,
    PatientPasswordSetAPIView,
    PatientRegistrationAPIView,
)

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='auth-login'),
    path('register/patient/', PatientRegistrationAPIView.as_view(), name='patient-register'),
    path('register/patient/verify-otp/', PatientOTPVerifyAPIView.as_view(), name='patient-verify-otp'),
    path('register/patient/password/', PatientPasswordSetAPIView.as_view(), name='patient-password-set'),
    path('register/password/', PatientPasswordSetAPIView.as_view(), name='register-password-set'),
    path('register/doctor/', DoctorRegistrationAPIView.as_view(), name='doctor-register'),
    path('register/doctor/verify-otp/', DoctorOTPVerifyAPIView.as_view(), name='doctor-verify-otp'),
    path('resend-otp/', ResendOTPAPIView.as_view(), name='resend-otp'),
    path('doctor/approve/<int:doctor_id>/', DoctorApprovalAPIView.as_view(), name='doctor-approve'),
    path('google/', GoogleSocialLoginAPIView.as_view(), name='google-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
