import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

import hash_service
from services.encryption_service import encrypt_file
from blockchain import blockchain_service
from .models import AuditLog, MedicalReport, BlockchainRecord


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

    def test_upload_creates_report_and_blockchain_and_audit(self):
        upload_url = reverse('upload')
        file_data = SimpleUploadedFile('report.pdf', b'hello world', content_type='application/pdf')
        response = self.client.post(upload_url, {
            'report_name': 'Test Upload',
            'category': 'other',
            'encrypted_file': file_data,
        }, secure=True, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report uploaded, encrypted, and verified successfully.')

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

        download_url = reverse('secure_report_download', args=[report.pk])
        response = self.client.get(download_url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuditLog.objects.filter(user=self.user, action='secure_download', report=report).count(), 1)
        input_path.unlink(missing_ok=True)

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
            temp_chain_file = Path(tempfile.gettempdir()) / 'chain_test.json'
            blockchain_service.BLOCKCHAIN_FILE = temp_chain_file
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
            temp_chain_file.unlink(missing_ok=True)
