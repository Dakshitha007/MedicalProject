import json
import os
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

import hash_service
from services.encryption_service import encrypt_file
from blockchain import blockchain_service
from .models import AuditLog, MedicalReport, BlockchainRecord, Consent, UserProfile


class HashServiceTests(SimpleTestCase):
	def test_file_sha256(self):
		data = b"hello world"
		tmp = Path(tempfile.gettempdir()) / "dv_test_hash.bin"
		tmp.write_bytes(data)
		try:
			h = hash_service.file_sha256(tmp)
			self.assertEqual(h, 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9')
		finally:
			tmp.unlink()


class BlockchainModelTests(TestCase):
    def test_create_blockchain_record(self):
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='pass')

        # create a dummy uploaded file
        uploaded = SimpleUploadedFile('report.pdf', b'pdfcontent', content_type='application/pdf')

        report = MedicalReport.objects.create(
            owner=user,
            report_name='Test Report',
            category='other',
            encrypted_file=uploaded,
            original_filename='report.pdf',
            file_hash='deadbeef',
            hash_value='deadbeef',
        )

        br = BlockchainRecord.objects.create(report=report, report_hash='deadbeef', transaction_reference='tx123')
        self.assertEqual(br.report, report)
        self.assertEqual(br.report_hash, 'deadbeef')


@override_settings(SECURE_SSL_REDIRECT=False)
class UploadWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='uploaduser', password='testpass')
        self.client = Client()
        self.client.defaults['wsgi.url_scheme'] = 'https'
        self.client.defaults['HTTP_HOST'] = '127.0.0.1'
        self.client.defaults['SERVER_PORT'] = '443'
        self.client.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'
        self.client.login(username='uploaduser', password='testpass')

        self.chain_file = Path(tempfile.gettempdir()) / f'blockchain_test_{uuid.uuid4().hex}.json'
        self.anchor_file = Path(tempfile.gettempdir()) / f'blockchain_anchor_test_{uuid.uuid4().hex}.json'
        blockchain_service.BLOCKCHAIN_FILE = self.chain_file
        blockchain_service.BLOCKCHAIN_ANCHOR_FILE = self.anchor_file
        if self.chain_file.exists():
            self.chain_file.unlink(missing_ok=True)
        if self.anchor_file.exists():
            self.anchor_file.unlink(missing_ok=True)

    def tearDown(self):
        if getattr(self, 'chain_file', None) and self.chain_file.exists():
            self.chain_file.unlink(missing_ok=True)
        if getattr(self, 'anchor_file', None) and self.anchor_file.exists():
            self.anchor_file.unlink(missing_ok=True)
        blockchain_service.BLOCKCHAIN_FILE = None
        blockchain_service.BLOCKCHAIN_ANCHOR_FILE = None

    def test_upload_creates_report_and_blockchain_and_audit(self):
        upload_url = reverse('upload')
        file_data = SimpleUploadedFile('report.pdf', b'%PDF-1.4\n%EOF\n', content_type='application/pdf')
        response = self.client.post(upload_url, {
            'report_name': 'Test Upload',
            'category': 'other',
            'encrypted_file': file_data,
        }, secure=True, follow=True)

        self.assertEqual(response.status_code, 200)
        report = MedicalReport.objects.get(report_name='Test Upload', owner=self.user)
        self.assertIsNotNone(report.hash_value)
        self.assertNotEqual(report.hash_value, '')
        self.assertEqual(report.verification_status, 'verified')
        self.assertEqual(report.blockchain_records.count(), 1)
        self.assertEqual(AuditLog.objects.filter(user=self.user, action='upload', report=report).count(), 1)

    def test_download_logs_audit(self):
        report = MedicalReport.objects.create(
            owner=self.user,
            report_name='Download Report',
            category='other',
            encrypted_file=SimpleUploadedFile('report.pdf', b'hello', content_type='application/pdf'),
            original_filename='report.pdf',
            hash_value='dummyhash',
            verification_status='verified',
        )

        download_url = reverse('report_download', args=[report.pk])
        response = self.client.get(download_url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuditLog.objects.filter(user=self.user, action='download', report=report).count(), 1)

    def test_secure_download_decrypts_and_audits(self):
        input_path = Path(tempfile.gettempdir()) / 'secure_download_test.txt'
        input_path.write_bytes(b'secret pdf content')
        encrypted_path = Path(settings.MEDIA_ROOT) / 'reports' / 'encrypted' / 'secure_test.pdf'
        encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = encrypt_file(input_path, encrypted_path, settings.FILE_ENCRYPTION_SECRET)

        report = MedicalReport.objects.create(
            owner=self.user,
            report_name='Secure Download Report',
            category='other',
            encrypted_file=str(encrypted_path.relative_to(settings.MEDIA_ROOT)).replace('\\', '/'),
            original_filename='secure_test.pdf',
            hash_value=hash_service.file_sha256(encrypted_path),
            verification_status='verified',
            encryption_metadata=metadata,
        )

        before_files = set(Path(tempfile.gettempdir()).glob('*'))
        download_url = reverse('secure_report_download', args=[report.pk])
        response = self.client.get(download_url, secure=True)
        self.assertEqual(response.status_code, 200)
        response.close()
        after_files = set(Path(tempfile.gettempdir()).glob('*'))
        self.assertEqual(after_files, before_files)
        self.assertEqual(AuditLog.objects.filter(user=self.user, action='secure_download', report=report).count(), 1)
        input_path.unlink(missing_ok=True)

    def test_failed_secure_download_cleans_temp_files(self):
        encrypted_path = Path(settings.MEDIA_ROOT) / 'reports' / 'encrypted' / 'broken_secure_test.pdf'
        encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted_path.write_bytes(b'not a valid encrypted blob')

        report = MedicalReport.objects.create(
            owner=self.user,
            report_name='Broken Secure Download Report',
            category='other',
            encrypted_file=str(encrypted_path.relative_to(settings.MEDIA_ROOT)).replace('\\', '/'),
            original_filename='broken_secure_test.pdf',
            hash_value='deadbeef',
            verification_status='verified',
            encryption_metadata={'version': 1, 'algorithm': 'AES-256-GCM', 'nonce': '', 'tag': ''},
        )

        before_files = set(Path(tempfile.gettempdir()).glob('*'))
        download_url = reverse('secure_report_download', args=[report.pk])
        response = self.client.get(download_url, secure=True)
        self.assertEqual(response.status_code, 404)
        after_files = set(Path(tempfile.gettempdir()).glob('*'))
        self.assertEqual(after_files, before_files)
        encrypted_path.unlink(missing_ok=True)

    def test_upload_sanitizes_malicious_filename(self):
        upload_url = reverse('upload')
        # Use valid PDF magic bytes to test filename sanitization separately from content validation.
        file_data = SimpleUploadedFile('../../evil.pdf', b'%PDF-1.4\n%EOF\n', content_type='application/pdf')
        response = self.client.post(upload_url, {
            'report_name': 'Malicious Upload',
            'category': 'other',
            'encrypted_file': file_data,
        }, secure=True, follow=True)

        self.assertEqual(response.status_code, 200)
        report = MedicalReport.objects.get(report_name='Malicious Upload', owner=self.user)
        self.assertNotIn('..', report.encrypted_file.name)
        self.assertTrue(report.encrypted_file.name.startswith('reports/encrypted/'))
        encrypted_path = Path(settings.MEDIA_ROOT).resolve() / report.encrypted_file.name
        self.assertTrue(encrypted_path.resolve().is_relative_to(Path(settings.MEDIA_ROOT).resolve()))
        self.assertTrue(encrypted_path.exists())

    def test_download_rejects_report_with_external_file_path(self):
        outside_path = Path(settings.MEDIA_ROOT).resolve().parent / 'outside.pdf'
        outside_path.write_bytes(b'attack content')
        report = MedicalReport.objects.create(
            owner=self.user,
            report_name='External Path Report',
            category='other',
            encrypted_file=str(outside_path),
            original_filename='outside.pdf',
            hash_value=hash_service.file_sha256(outside_path),
            verification_status='verified',
            encryption_metadata={'version': 1, 'algorithm': 'AES-256-GCM', 'nonce': '', 'tag': ''},
        )

        download_url = reverse('report_download', args=[report.pk])
        response = self.client.get(download_url, secure=True)
        self.assertEqual(response.status_code, 404)

        secure_download_url = reverse('secure_report_download', args=[report.pk])
        response = self.client.get(secure_download_url, secure=True)
        self.assertEqual(response.status_code, 404)
        outside_path.unlink(missing_ok=True)

    def test_other_user_cannot_access_report(self):
        other_user = get_user_model().objects.create_user(username='otheruser', password='otherpass')
        report = MedicalReport.objects.create(
            owner=other_user,
            report_name='Private Report',
            category='other',
            encrypted_file=SimpleUploadedFile('private.pdf', b'private', content_type='application/pdf'),
            original_filename='private.pdf',
            hash_value='privatehash',
            verification_status='verified',
        )

        download_url = reverse('secure_report_download', args=[report.pk])
        response = self.client.get(download_url, secure=True)
        self.assertEqual(response.status_code, 404)

    def test_blockchain_tamper_detection(self):
        with patch.dict(os.environ, {'BLOCKCHAIN_SIGNING_SECRET': 'testsigsecret', 'FILE_ENCRYPTION_SECRET': 'testsigsecret'}):
            original_chain_file = blockchain_service.BLOCKCHAIN_FILE
            original_anchor_file = blockchain_service.BLOCKCHAIN_ANCHOR_FILE
            try:
                temp_chain_file = Path(tempfile.gettempdir()) / 'chain_test.json'
                temp_anchor_file = Path(tempfile.gettempdir()) / 'anchor_test.json'
                blockchain_service.BLOCKCHAIN_FILE = temp_chain_file
                blockchain_service.BLOCKCHAIN_ANCHOR_FILE = temp_anchor_file
                chain = {'chain': [
                    {
                        'index': 1,
                        'timestamp': 1.0,
                        'previous_hash': '0' * 64,
                        'hash': 'abc123',
                        'signature': 'sig1',
                        'data': {
                            'report_id': 1,
                            'user_id': self.user.id,
                            'file_hash': 'deadbeef',
                            'timestamp': 1.0,
                        },
                    }
                ]}
                temp_chain_file.write_text(json.dumps(chain), encoding='utf-8')
                self.assertFalse(blockchain_service.is_chain_valid())
            finally:
                temp_chain_file.unlink(missing_ok=True)
                temp_anchor_file.unlink(missing_ok=True)
                blockchain_service.BLOCKCHAIN_FILE = original_chain_file
                blockchain_service.BLOCKCHAIN_ANCHOR_FILE = original_anchor_file


class AuthorizationAttackTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.patient_a = User.objects.create_user(username='patient_a', password='pass')
        self.patient_b = User.objects.create_user(username='patient_b', password='pass')
        self.doctor = User.objects.create_user(username='doctor', password='pass')
        self.admin = User.objects.create_user(username='admin_user', password='pass', is_staff=True, is_superuser=True)

        self.patient_a_profile = UserProfile.objects.create(user=self.patient_a, role='patient')
        self.patient_b_profile = UserProfile.objects.create(user=self.patient_b, role='patient')
        self.doctor_profile = UserProfile.objects.create(user=self.doctor, role='doctor')
        self.doctor_profile.assigned_patients.add(self.patient_b)

        self.chain_file = Path(tempfile.gettempdir()) / f'auth_blockchain_test_{uuid.uuid4().hex}.json'
        self.anchor_file = Path(tempfile.gettempdir()) / f'auth_blockchain_anchor_test_{uuid.uuid4().hex}.json'
        blockchain_service.BLOCKCHAIN_FILE = self.chain_file
        blockchain_service.BLOCKCHAIN_ANCHOR_FILE = self.anchor_file
        if self.chain_file.exists():
            self.chain_file.unlink(missing_ok=True)
        if self.anchor_file.exists():
            self.anchor_file.unlink(missing_ok=True)

        self.report_b = MedicalReport.objects.create(
            owner=self.patient_b,
            report_name='Patient B Report',
            category='other',
            encrypted_file=SimpleUploadedFile('report_b.pdf', b'secret', content_type='application/pdf'),
            original_filename='report_b.pdf',
            hash_value='hashb',
            verification_status='verified',
        )

        self.client = Client()
        self.client.defaults['wsgi.url_scheme'] = 'https'
        self.client.defaults['HTTP_HOST'] = '127.0.0.1'
        self.client.defaults['SERVER_PORT'] = '443'
        self.client.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'

    def test_patient_a_cannot_access_patient_b_report_detail(self):
        self.client.login(username='patient_a', password='pass')
        response = self.client.get(reverse('report_detail', args=[self.report_b.pk]), secure=True)
        self.assertEqual(response.status_code, 404)

    def test_patient_a_cannot_download_patient_b_report(self):
        self.client.login(username='patient_a', password='pass')
        response = self.client.get(reverse('report_download', args=[self.report_b.pk]), secure=True)
        self.assertEqual(response.status_code, 404)

    def test_patient_a_cannot_delete_patient_b_report(self):
        self.client.login(username='patient_a', password='pass')
        response = self.client.post(reverse('report_delete', args=[self.report_b.pk]), secure=True, follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(MedicalReport.objects.filter(pk=self.report_b.pk).exists())

    def test_doctor_without_consent_cannot_access_patient_b_report(self):
        self.client.login(username='doctor', password='pass')
        response = self.client.get(reverse('report_detail', args=[self.report_b.pk]), secure=True)
        self.assertEqual(response.status_code, 404)

    def test_doctor_with_revoked_consent_cannot_access_patient_b_report(self):
        Consent.objects.create(
            patient=self.patient_b,
            doctor=self.doctor,
            scope='read',
            purpose='test',
            revoked=True,
        )
        self.client.login(username='doctor', password='pass')
        response = self.client.get(reverse('report_detail', args=[self.report_b.pk]), secure=True)
        self.assertEqual(response.status_code, 404)

    def tearDown(self):
        if getattr(self, 'chain_file', None) and self.chain_file.exists():
            self.chain_file.unlink(missing_ok=True)
        if getattr(self, 'anchor_file', None) and self.anchor_file.exists():
            self.anchor_file.unlink(missing_ok=True)
        blockchain_service.BLOCKCHAIN_FILE = None
        blockchain_service.BLOCKCHAIN_ANCHOR_FILE = None

    def test_doctor_with_expired_consent_cannot_access_patient_b_report(self):
        Consent.objects.create(
            patient=self.patient_b,
            doctor=self.doctor,
            scope='read',
            purpose='test',
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.client.login(username='doctor', password='pass')
        response = self.client.get(reverse('report_detail', args=[self.report_b.pk]), secure=True)
        self.assertEqual(response.status_code, 404)

    def test_patient_cannot_create_appointment_via_legacy_api(self):
        self.client.login(username='patient_a', password='pass')
        response = self.client.post(
            reverse('appointments_create'),
            data=json.dumps({'patient': 'patient_a', 'scheduled_at': '2026-01-01T12:00:00Z'}),
            content_type='application/json',
            secure=True,
        )
        self.assertEqual(response.status_code, 403)
