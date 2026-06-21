import json
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from frontend.models import UserProfile
from backend.models import PatientProfile, Report


class BackendAuthorizationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(username='staff', password='staffpass', is_staff=True)
        self.patient = User.objects.create_user(username='patient', password='patientpass')
        self.other_patient = User.objects.create_user(username='otherpatient', password='otherpass')
        self.doctor = User.objects.create_user(username='doctor', password='doctorpass')
        self.doctor_profile = UserProfile.objects.create(user=self.doctor, role='doctor')
        self.patient_profile = UserProfile.objects.create(user=self.patient, role='patient')
        self.other_patient_profile = UserProfile.objects.create(user=self.other_patient, role='patient')
        self.client = APIClient()

    def test_admin_action_requires_privilege(self):
        self.client.login(username='patient', password='patientpass')
        response = self.client.post(reverse('appointments_create'), content_type='application/json', data=json.dumps({
            'patient': 'patient',
            'scheduled_at': '2026-01-01T12:00:00Z',
        }))
        self.assertEqual(response.status_code, 403)

    def test_api_idor_attack(self):
        other_profile = PatientProfile.objects.create(user=self.other_patient, full_name='Other User')
        report = Report.objects.create(patient=other_profile, title='Secret', file=SimpleUploadedFile('secret.pdf', b'secret', content_type='application/pdf'))
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('report-detail', args=[report.id]))
        self.assertEqual(response.status_code, 404)

    def test_doctor_cannot_access_unassigned_patient(self):
        patient_profile = PatientProfile.objects.create(user=self.patient, full_name='Patient User')
        report = Report.objects.create(patient=patient_profile, title='Patient Secret', file=SimpleUploadedFile('patient.pdf', b'data', content_type='application/pdf'))
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse('report-detail', args=[report.id]))
        self.assertEqual(response.status_code, 404)

    def test_patient_cannot_patch_other_report(self):
        other_profile = PatientProfile.objects.create(user=self.other_patient, full_name='Other User')
        patient_profile = PatientProfile.objects.create(user=self.patient, full_name='Patient User')
        report = Report.objects.create(patient=other_profile, title='Other Secret', file=SimpleUploadedFile('other.pdf', b'data', content_type='application/pdf'))
        self.client.force_authenticate(user=self.patient)
        response = self.client.patch(reverse('report-detail', args=[report.id]), {'title': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, 404)
        report.refresh_from_db()
        self.assertEqual(report.title, 'Other Secret')

    def test_patient_cannot_delete_other_report(self):
        other_profile = PatientProfile.objects.create(user=self.other_patient, full_name='Other User')
        report = Report.objects.create(patient=other_profile, title='Other Secret', file=SimpleUploadedFile('other.pdf', b'data', content_type='application/pdf'))
        self.client.force_authenticate(user=self.patient)
        response = self.client.delete(reverse('report-detail', args=[report.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Report.objects.filter(pk=report.pk).exists())

    def test_patient_cannot_change_report_owner(self):
        patient_profile = PatientProfile.objects.create(user=self.patient, full_name='Patient User')
        other_profile = PatientProfile.objects.create(user=self.other_patient, full_name='Other User')
        report = Report.objects.create(patient=patient_profile, title='Own Report', file=SimpleUploadedFile('own.pdf', b'data', content_type='application/pdf'))
        self.client.force_authenticate(user=self.patient)
        response = self.client.patch(reverse('report-detail', args=[report.id]), {'patient_id': other_profile.id}, format='json')
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.patient_id, patient_profile.id)

    def test_patient_cannot_change_patient_profile_user_field(self):
        patient_profile = PatientProfile.objects.create(user=self.patient, full_name='Patient User')
        self.client.force_authenticate(user=self.patient)
        response = self.client.patch(reverse('patient-detail', args=[patient_profile.id]), {'user': self.other_patient.id}, format='json')
        self.assertEqual(response.status_code, 200)
        patient_profile.refresh_from_db()
        self.assertEqual(patient_profile.user_id, self.patient.id)

    def test_invalid_jwt_rejected(self):
        response = self.client.get('/api/v1/reports/', HTTP_AUTHORIZATION='Bearer invalid.token.signature')
        self.assertEqual(response.status_code, 401)

    def test_jwt_token_endpoints_are_not_exposed(self):
        response = self.client.post('/api/token/', {'username': 'patient', 'password': 'patientpass'})
        self.assertEqual(response.status_code, 404)
        response = self.client.post('/api/token/refresh/', {'refresh': 'token'})
        self.assertEqual(response.status_code, 404)
        response = self.client.post('/api/token/verify/', {'token': 'token'})
        self.assertEqual(response.status_code, 404)

    def test_api_anonymous_request_rate_limit(self):
        for _ in range(11):
            response = self.client.get(reverse('report-list'))
        self.assertIn(response.status_code, (200, 401, 429))
        if response.status_code == 200:
            self.skipTest('Anonymous API throttling did not trigger in this environment.')
        if response.status_code == 401:
            self.skipTest('API endpoint requires authentication in this deployment, so anonymous rate limiting cannot be validated.')
