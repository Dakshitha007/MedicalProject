import secrets
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, OTPVerification
from .serializers import (
    DoctorRegistrationSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    OTPVerifySerializer,
    PasswordSetSerializer,
    PatientRegistrationSerializer,
)
from .services import build_jwt_tokens, create_login_history, send_registration_otp, verify_otp_code
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from .utils import get_email_domain, get_hospital_domains
from .permissions import IsAdminUser


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data or {}
        identifier = (data.get('email_or_username') or '').strip()
        if '@' in identifier:
            identifier = identifier.lower()
        password = data.get('password')
        role = data.get('role')

        if not identifier:
            return Response({'detail': 'Email or username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'detail': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if role not in [User.ROLE_PATIENT, User.ROLE_DOCTOR, User.ROLE_ADMIN]:
            return Response({'detail': 'Role selection is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(models.Q(email__iexact=identifier) | models.Q(username__iexact=identifier)).first()
        if user:
            if user.role != role:
                create_login_history(identifier, user=user, successful=False, request=request, note='Role mismatch')
                return Response({'detail': 'Selected role does not match this account.'}, status=status.HTTP_403_FORBIDDEN)
            if not user.is_active:
                create_login_history(identifier, user=user, successful=False, request=request, note='Inactive user')
                return Response({'detail': 'Account is not active. Verify your OTP or wait for admin approval.'}, status=status.HTTP_403_FORBIDDEN)
            if not user.is_verified:
                create_login_history(identifier, user=user, successful=False, request=request, note='Not verified')
                return Response({'detail': 'Your account is not verified yet. Complete OTP verification before logging in.'}, status=status.HTTP_403_FORBIDDEN)
            if not user.has_usable_password():
                create_login_history(identifier, user=user, successful=False, request=request, note='Password not set')
                return Response({'detail': 'A password is not set for this account. Complete registration or reset your password.'}, status=status.HTTP_403_FORBIDDEN)

        user = authenticate(request=request, username=identifier, password=password)
        if user is None:
            create_login_history(identifier, successful=False, request=request)
            return Response({'detail': 'Invalid credentials or user does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)

        create_login_history(identifier, user=user, successful=True, request=request)
        tokens = build_jwt_tokens(user)
        return Response(tokens, status=status.HTTP_200_OK)


class PatientRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        existing = User.objects.filter(email__iexact=email).first() if email else None
        if existing:
            if existing.role != User.ROLE_PATIENT:
                return Response({'detail': 'This email is already registered with a different role.'}, status=status.HTTP_400_BAD_REQUEST)
            if not existing.is_verified or not existing.is_active or not existing.has_usable_password():
                otp = send_registration_otp(existing, purpose=OTPVerification.PURPOSE_REGISTRATION)
                payload = {'detail': 'Your registration is already in progress. A new OTP has been sent.'}
                if settings.DEBUG and otp:
                    payload['debug_otp'] = otp.code
                patient_profile = PatientProfile.objects.filter(user=existing).first()
                if patient_profile and patient_profile.patient_id:
                    payload['patient_id'] = patient_profile.patient_id
                return Response(payload, status=status.HTTP_200_OK)
            return Response({'detail': 'A patient with this email already exists. Please log in instead.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PatientRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        patient_profile = PatientProfile.objects.filter(user=user).first()
        patient_id = patient_profile.patient_id if patient_profile else None
        if settings.DEBUG:
            otp = OTPVerification.objects.filter(email__iexact=user.email, purpose=OTPVerification.PURPOSE_REGISTRATION).order_by('-created_at').first()
            return Response({'detail': 'Patient registration started. OTP has been sent to the provided contact.', 'patient_id': patient_id, 'debug_otp': otp.code if otp else None}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Patient registration started. OTP has been sent to the provided contact.', 'patient_id': patient_id}, status=status.HTTP_201_CREATED)


class PatientOTPVerifyAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        user = otp.user or User.objects.filter(email__iexact=request.data.get('email')).first()
        if not user:
            return Response({'detail': 'Patient account not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.is_verified = True
        user.is_active = True
        user.save(update_fields=['is_verified', 'is_active'])
        # Ensure patient profile has patient_id and is saved
        patient_profile = PatientProfile.objects.filter(user=user).first()
        patient_id = None
        if patient_profile:
            if not patient_profile.patient_id:
                patient_profile.save()
            patient_id = patient_profile.patient_id
        return Response({'detail': 'OTP verified. Complete your password setup to log in.', 'patient_id': patient_id}, status=status.HTTP_200_OK)


class PatientPasswordSetAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = build_jwt_tokens(user)
        payload = tokens
        payload['role'] = user.role
        return Response(payload, status=status.HTTP_200_OK)


class DoctorRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        existing = User.objects.filter(email__iexact=email).first() if email else None
        if existing:
            if existing.role != User.ROLE_DOCTOR:
                return Response({'detail': 'This email is already registered with a different role.'}, status=status.HTTP_400_BAD_REQUEST)
            if not existing.is_verified or not existing.is_active:
                otp = send_registration_otp(existing, purpose=OTPVerification.PURPOSE_DOCTOR_CONFIRM)
                payload = {'detail': 'Your doctor registration is already in progress. A new OTP has been sent.'}
                if settings.DEBUG and otp:
                    payload['debug_otp'] = otp.code
                return Response(payload, status=status.HTTP_200_OK)
            return Response({'detail': 'A doctor with this email already exists. Please log in instead.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DoctorRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Doctor registration submitted. OTP has been sent for mobile/email verification.'}, status=status.HTTP_201_CREATED)


class DoctorOTPVerifyAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        user = otp.user or User.objects.filter(email__iexact=request.data.get('email')).first()
        if not user:
            return Response({'detail': 'Doctor account not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.is_verified = True
        user.is_active = True
        user.save(update_fields=['is_verified', 'is_active'])
        doctor_profile = DoctorProfile.objects.filter(user=user).first()
        if doctor_profile:
            doctor_profile.verification_status = 'approved'
            doctor_profile.is_doctor_verified = True
            doctor_profile.save(update_fields=['verification_status', 'is_doctor_verified'])
        return Response({'detail': 'OTP verified. Your doctor account is active and you may now log in.', 'status': 'active'}, status=status.HTTP_200_OK)


class DoctorApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, doctor_id):
        doctor_profile = get_object_or_404(DoctorProfile, pk=doctor_id)
        doctor_profile.verification_status = 'approved'
        doctor_profile.is_doctor_verified = True
        doctor_profile.save(update_fields=['verification_status', 'is_doctor_verified'])
        doctor_profile.user.is_active = True
        doctor_profile.user.save(update_fields=['is_active'])
        return Response({'detail': 'Doctor verification approved.'}, status=status.HTTP_200_OK)


class GoogleSocialLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['id_token']
        google_verify_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={token}'
        response = requests.get(google_verify_url)
        if response.status_code != 200:
            return Response({'detail': 'Invalid Google token.'}, status=status.HTTP_400_BAD_REQUEST)
        payload = response.json()
        if payload.get('aud') != settings.GOOGLE_CLIENT_ID:
            return Response({'detail': 'Google client mismatch.'}, status=status.HTTP_400_BAD_REQUEST)
        email = payload.get('email')
        if not email:
            return Response({'detail': 'Google account email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        email = email.strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        role = serializer.validated_data['role']
        if user:
            if user.role != role:
                return Response({'detail': 'Role mismatch for existing Google user.'}, status=status.HTTP_400_BAD_REQUEST)
            if not user.is_active:
                return Response({'detail': 'User account is not active.'}, status=status.HTTP_403_FORBIDDEN)
            tokens = build_jwt_tokens(user)
            return Response(tokens, status=status.HTTP_200_OK)

        username = serializer.validated_data.get('username') or email.split('@')[0]
        if User.objects.filter(username__iexact=username).exists():
            username = f"{username}_{secrets.token_hex(3)}"
        user = User.objects.create_user(
            email=email,
            username=username,
            password=None,
            role=role,
            phone_number=serializer.validated_data.get('phone_number', ''),
            is_active=False,
            is_verified=False,
        )
        if role == User.ROLE_PATIENT:
            PatientProfile.objects.create(
                user=user,
                full_name=serializer.validated_data.get('full_name', ''),
                phone=user.phone_number,
                address='',
                emergency_contact='',
            )
            send_registration_otp(user, purpose=OTPVerification.PURPOSE_GOOGLE_LOGIN)
            return Response({'detail': 'Google login detected. Patient OTP sent and verification required.'}, status=status.HTTP_201_CREATED)
        doctor_profile = DoctorProfile.objects.create(
            user=user,
            full_name=serializer.validated_data.get('full_name', ''),
            hospital_name=serializer.validated_data.get('hospital_name', ''),
            specialization=serializer.validated_data.get('specialization', ''),
            medical_license_number=serializer.validated_data.get('medical_license_number', ''),
            years_of_experience=serializer.validated_data.get('years_of_experience', 0),
            hospital_email_domain=get_email_domain(email),
            verification_status='pending',
            is_doctor_verified=False,
        )
        send_registration_otp(user, purpose=OTPVerification.PURPOSE_DOCTOR_CONFIRM)
        return Response({'detail': 'Google login detected. Doctor registration pending OTP and admin approval.'}, status=status.HTTP_201_CREATED)


class ResendOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        email = data.get('email', '').strip().lower()
        phone_number = data.get('phone_number', '').strip() if data.get('phone_number') else None
        purpose = data.get('purpose', OTPVerification.PURPOSE_REGISTRATION)

        if not email and not phone_number:
            return Response({'detail': 'Email or phone number is required to resend OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        if not user and phone_number:
            user = User.objects.filter(phone_number=phone_number).first()

        if not user:
            return Response({'detail': 'No user found for the provided contact.'}, status=status.HTTP_404_NOT_FOUND)

        otp = send_registration_otp(user, purpose=purpose)
        payload = {'detail': 'A new OTP has been sent.'}
        patient_profile = PatientProfile.objects.filter(user=user).first()
        if patient_profile and patient_profile.patient_id:
            payload['patient_id'] = patient_profile.patient_id
        if settings.DEBUG and otp:
            payload['debug_otp'] = otp.code
        return Response(payload, status=status.HTTP_200_OK)
