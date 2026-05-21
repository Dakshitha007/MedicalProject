from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from authentication.models import User, OTPVerification
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from appointments.models import Appointment
from reports.models import MedicalReport


class Command(BaseCommand):
    help = 'Seed test data for development and testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting seed process...'))

        # Create test patients
        patient_users = []
        for i in range(1, 4):
            email = f'patient{i}@example.com'
            username = f'patient{i}'
            
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    username=username,
                    password='PatientPass123!',
                    role=User.ROLE_PATIENT,
                    phone_number=f'+123456789{i}',
                    is_verified=True,
                    is_active=True,
                )
                patient_users.append(user)
                self.stdout.write(self.style.SUCCESS(f'✓ Created patient user: {email}'))
            else:
                patient_users.append(User.objects.get(email=email))

        # Create patient profiles
        patient_profiles = []
        for i, user in enumerate(patient_users, 1):
            if not PatientProfile.objects.filter(user=user).exists():
                profile = PatientProfile.objects.create(
                    user=user,
                    full_name=f'Patient {i}',
                    age=25 + i * 5,
                    gender=['male', 'female', 'other'][i % 3],
                    address=f'{100 + i} Main Street',
                    emergency_contact=f'Emergency Contact {i}'
                )
                patient_profiles.append(profile)
                self.stdout.write(self.style.SUCCESS(f'✓ Created patient profile: {profile.patient_id}'))
            else:
                patient_profiles.append(PatientProfile.objects.get(user=user))

        # Create test doctors
        doctor_users = []
        for i in range(1, 3):
            email = f'doctor{i}@example.com'
            username = f'doctor{i}'
            
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    username=username,
                    password='DoctorPass123!',
                    role=User.ROLE_DOCTOR,
                    phone_number=f'+198765432{i}',
                    is_verified=True,
                    is_active=True,
                )
                doctor_users.append(user)
                self.stdout.write(self.style.SUCCESS(f'✓ Created doctor user: {email}'))
            else:
                doctor_users.append(User.objects.get(email=email))

        # Create doctor profiles
        doctor_profiles = []
        specializations = ['Cardiology', 'Neurology', 'Orthopedics']
        hospitals = ['City Hospital', 'General Medical Center', 'Regional Health']
        
        for i, user in enumerate(doctor_users, 1):
            if not DoctorProfile.objects.filter(user=user).exists():
                profile = DoctorProfile.objects.create(
                    user=user,
                    full_name=f'Dr. Smith {i}',
                    hospital_name=hospitals[i - 1],
                    specialization=specializations[i - 1],
                    medical_license_number=f'MD{100000 + i}',
                    years_of_experience=5 + i,
                    verification_status='approved',
                    verified_at=timezone.now()
                )
                doctor_profiles.append(profile)
                self.stdout.write(self.style.SUCCESS(f'✓ Created doctor profile: {user.email}'))
            else:
                doctor_profiles.append(DoctorProfile.objects.get(user=user))

        # Create test appointments
        for patient_profile in patient_profiles:
            for doctor_profile in doctor_profiles[:1]:  # Assign to first doctor
                if not Appointment.objects.filter(
                    patient=patient_profile,
                    doctor=doctor_profile
                ).exists():
                    appointment = Appointment.objects.create(
                        patient=patient_profile,
                        doctor=doctor_profile,
                        booked_by=patient_profile.user,
                        scheduled_at=timezone.now() + timedelta(days=7),
                        reason='Regular checkup',
                        status='scheduled'
                    )
                    self.stdout.write(self.style.SUCCESS(f'✓ Created appointment {appointment.id}'))

        # Create test medical reports
        for i, doctor_user in enumerate(doctor_users, 1):
            for patient_profile in patient_profiles[:1]:
                if not MedicalReport.objects.filter(
                    uploaded_by=doctor_user,
                    patient=patient_profile
                ).exists():
                    report = MedicalReport.objects.create(
                        patient=patient_profile,
                        uploaded_by=doctor_user,
                        diagnosis=f'Test Diagnosis {i}',
                        prescription=f'Test Prescription {i}',
                        file='reports/sample.pdf'
                    )
                    self.stdout.write(self.style.SUCCESS(f'✓ Created medical report {report.id}'))

        self.stdout.write(self.style.SUCCESS('\n=== SEED DATA CREATED ===\n'))
        self.stdout.write(self.style.WARNING('TEST CREDENTIALS:'))
        self.stdout.write(self.style.SUCCESS('Admin: admin@local / AdminPass123'))
        self.stdout.write(self.style.SUCCESS('Patient 1: patient1@example.com / PatientPass123!'))
        self.stdout.write(self.style.SUCCESS('Patient 2: patient2@example.com / PatientPass123!'))
        self.stdout.write(self.style.SUCCESS('Patient 3: patient3@example.com / PatientPass123!'))
        self.stdout.write(self.style.SUCCESS('Doctor 1: doctor1@example.com / DoctorPass123!'))
        self.stdout.write(self.style.SUCCESS('Doctor 2: doctor2@example.com / DoctorPass123!'))
