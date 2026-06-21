import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcloud.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from services.encryption_service import encrypt_file, decrypt_file
from frontend.models import MedicalReport
from frontend.utils import get_report_for_user

User = get_user_model()
# Ensure clean user name for test run
user, created = User.objects.get_or_create(username='secureuser_debug')
if created:
    user.set_password('testpass')
    user.save()

print('user id', user.id)
print('has profile attr', hasattr(user, 'userprofile'))
try:
    profile = user.userprofile
    print('profile exists', profile)
except Exception as exc:
    print('profile exception', type(exc).__name__, exc)

input_path = Path(settings.MEDIA_ROOT) / 'reports' / 'encrypted' / 'secure_test_debug.txt'
input_path.parent.mkdir(parents=True, exist_ok=True)
input_path.write_bytes(b'secret pdf content')

output_path = input_path.with_suffix('.bin')
metadata = encrypt_file(input_path, output_path, settings.FILE_ENCRYPTION_SECRET)
print('encrypted path', output_path)
print('file exists', output_path.exists())
print('metadata', metadata)

report, _ = MedicalReport.objects.get_or_create(
    owner=user,
    report_name='Secure Download Report Debug',
    defaults={
        'category': 'other',
        'encrypted_file': str(output_path.relative_to(settings.MEDIA_ROOT)).replace('\\', '/'),
        'original_filename': 'secure_test.pdf',
        'hash_value': 'dummyhash',
        'verification_status': 'verified',
        'encryption_metadata': metadata,
    }
)
print('report id', report.id)
print('report encrypted_file name', report.encrypted_file.name)
print('report encrypted_file path', report.encrypted_file.path)
print('report file exists', Path(report.encrypted_file.path).exists())

try:
    found = get_report_for_user(user, report.pk)
    print('get_report_for_user succeeded', found.id)
except Exception as exc:
    print('get_report_for_user exception', type(exc).__name__, exc)

try:
    decrypt_target = Path(settings.MEDIA_ROOT) / 'reports' / 'encrypted' / 'decrypted_debug.txt'
    decrypt_file(output_path, settings.FILE_ENCRYPTION_SECRET, metadata, decrypt_target)
    print('decrypted contents', decrypt_target.read_bytes())
except Exception as exc:
    print('decrypt exception', type(exc).__name__, exc)
