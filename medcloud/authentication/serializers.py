import secrets
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import OTPVerification, User
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from .services import build_jwt_tokens, create_login_history, send_registration_otp, verify_otp_code
from .utils import get_email_domain, get_hospital_domains, validate_license_number


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role', 'phone_number', 'is_verified', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_verified', 'is_active', 'created_at']


class LoginSerializer(serializers.Serializer):
    email_or_username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[User.ROLE_PATIENT, User.ROLE_DOCTOR], write_only=True)

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)

    def validate(self, attrs):
        identifier = attrs.get('email_or_username')
        password = attrs.get('password')
        role = attrs.get('role')
        user = authenticate(request=self.context.get('request'), username=identifier, password=password)
        if user is None:
            create_login_history(identifier, successful=False, request=self.context.get('request'))
            raise serializers.ValidationError({'detail': 'Invalid credentials or user does not exist.'})
        if user.role != role:
            create_login_history(identifier, user=user, successful=False, request=self.context.get('request'), note='Role mismatch')
            raise serializers.ValidationError({'detail': 'Selected role does not match this account.'})
        if not user.is_active:
            create_login_history(identifier, user=user, successful=False, request=self.context.get('request'), note='Inactive user')
            raise serializers.ValidationError({'detail': 'Account is not active. Verify your email or wait for approval.'})
        create_login_history(identifier, user=user, successful=True, request=self.context.get('request'))
        tokens = build_jwt_tokens(user)
        return tokens


class PatientRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    age = serializers.IntegerField(min_value=0)
    gender = serializers.ChoiceField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    phone_number = serializers.CharField(max_length=32)
    address = serializers.CharField(max_length=512)
    emergency_contact = serializers.CharField(max_length=128)
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def create(self, validated_data):
        username = validated_data['email'].split('@')[0]
        if User.objects.filter(username__iexact=username).exists():
            username = f"{username}_{secrets.token_hex(3)}"
        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            password=None,
            role=User.ROLE_PATIENT,
            phone_number=validated_data['phone_number'],
            is_active=False,
            is_verified=False,
        )
        PatientProfile.objects.create(
            user=user,
            full_name=validated_data['full_name'],
            age=validated_data['age'],
            gender=validated_data['gender'],
            address=validated_data['address'],
            emergency_contact=validated_data['emergency_contact'],
        )
        send_registration_otp(user, purpose=OTPVerification.PURPOSE_REGISTRATION)
        return user


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=32, required=False)
    code = serializers.CharField(max_length=8)
    purpose = serializers.ChoiceField(choices=OTPVerification.PURPOSE_CHOICES)

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        if not email and not phone_number:
            raise serializers.ValidationError({'detail': 'Email or phone number is required for OTP verification.'})
        code = attrs.get('code')
        purpose = attrs.get('purpose')
        otp, error = verify_otp_code(email=email, phone_number=phone_number, code=code, purpose=purpose)
        if error:
            raise serializers.ValidationError({'detail': error})
        attrs['otp'] = otp
        return attrs


class PasswordSetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Password confirmation does not match.'})

        try:
            validate_password(attrs['password'], user=None)
        except Exception as exc:
            raise serializers.ValidationError({'password': [str(e) for e in exc]})

        return attrs

    def save(self):
        user = User.objects.get(email__iexact=self.validated_data['email'])
        user.set_password(self.validated_data['password'])
        user.is_active = True
        user.is_verified = True
        user.save(update_fields=['password', 'is_active', 'is_verified'])
        return user


class DoctorRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    hospital_name = serializers.CharField(max_length=256)
    specialization = serializers.CharField(max_length=128)
    medical_license_number = serializers.CharField(max_length=32)
    years_of_experience = serializers.IntegerField(min_value=0)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=32)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_medical_license_number(self, value):
        if not validate_license_number(value):
            raise serializers.ValidationError('Medical license number format is invalid.')
        return value.upper()

    def create(self, validated_data):
        username = validated_data['email'].split('@')[0]
        if User.objects.filter(username__iexact=username).exists():
            username = f"{username}_{secrets.token_hex(3)}"
        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            password=None,
            role=User.ROLE_DOCTOR,
            phone_number=validated_data['phone_number'],
            is_active=False,
            is_verified=False,
        )
        doctor_profile = DoctorProfile.objects.create(
            user=user,
            full_name=validated_data['full_name'],
            hospital_name=validated_data['hospital_name'],
            specialization=validated_data['specialization'],
            medical_license_number=validated_data['medical_license_number'],
            years_of_experience=validated_data['years_of_experience'],
            hospital_email_domain=get_email_domain(validated_data['email']),
            verification_status='pending',
            is_doctor_verified=False,
        )
        send_registration_otp(user, purpose=OTPVerification.PURPOSE_DOCTOR_CONFIRM)
        return user


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[User.ROLE_PATIENT, User.ROLE_DOCTOR], required=False)
    email = serializers.EmailField(required=False)
    username = serializers.CharField(max_length=150, required=False)
    full_name = serializers.CharField(max_length=200, required=False)
    phone_number = serializers.CharField(max_length=32, required=False)
    hospital_name = serializers.CharField(max_length=256, required=False)
    specialization = serializers.CharField(max_length=128, required=False)
    medical_license_number = serializers.CharField(max_length=32, required=False)
    years_of_experience = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs):
        if attrs.get('role') not in [User.ROLE_PATIENT, User.ROLE_DOCTOR]:
            raise serializers.ValidationError({'role': 'Role is required for Google login.'})
        return attrs
