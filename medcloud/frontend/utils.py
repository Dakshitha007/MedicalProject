import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import AuditLog, MedicalReport, Consent
from services.siem_service import send_audit_event


logger = logging.getLogger(__name__)


def _load_audit_chain():
    chain_path = Path(settings.AUDIT_CHAIN_FILE_PATH)
    if not chain_path.exists():
        return {'chain': []}
    try:
        with chain_path.open('r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise RuntimeError('Audit chain file is malformed or unreadable.') from exc


def _save_audit_chain(chain_data):
    chain_path = Path(settings.AUDIT_CHAIN_FILE_PATH)
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(chain_path.parent), prefix='audit_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(chain_data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, str(chain_path))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _compute_audit_entry_hash(entry_data, previous_hash: str) -> str:
    payload = {
        'previous_hash': previous_hash,
        'timestamp': entry_data.get('timestamp'),
        'user': entry_data.get('user'),
        'action': entry_data.get('action'),
        'report_id': entry_data.get('report_id'),
        'details': entry_data.get('details'),
        'ip_address': entry_data.get('ip_address'),
    }
    normalized = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _append_audit_chain_entry(audit):
    chain = _load_audit_chain().get('chain', [])
    previous_hash = chain[-1].get('entry_hash') if chain else '0' * 64
    entry = {
        'audit_id': audit.id,
        'timestamp': audit.timestamp.isoformat(),
        'user': audit.user.username,
        'action': audit.action,
        'report_id': audit.report_id if audit.report else None,
        'details': audit.details,
        'ip_address': audit.ip_address,
        'previous_hash': previous_hash,
    }
    entry['entry_hash'] = _compute_audit_entry_hash(entry, previous_hash)
    chain.append(entry)
    _save_audit_chain({'chain': chain})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit(user, action, request=None, report=None, details=None):
    with transaction.atomic():
        audit = AuditLog.objects.create(
            user=user,
            action=action,
            ip_address=get_client_ip(request) if request else None,
            report=report,
            details=details,
        )
        try:
            _append_audit_chain_entry(audit)
        except Exception as exc:
            if settings.AUDIT_CHAIN_ENFORCE:
                raise
            logger.exception('Audit chain append failed, continuing without anchor: %s', exc)
    if settings.SIEM_INGEST_URL and settings.SIEM_API_TOKEN:
        payload = {
            'event_type': 'audit',
            'user': user.username if user else 'anonymous',
            'action': action,
            'report_id': report.id if report else None,
            'ip_address': audit.ip_address,
            'details': details,
            'timestamp': audit.timestamp.isoformat(),
        }
        send_audit_event(payload)
    return audit


def get_accessible_reports(user):
    if hasattr(user, 'userprofile'):
        profile = user.userprofile
        if profile.is_admin or user.is_superuser:
            return MedicalReport.objects.all()
        if profile.is_doctor:
            assigned_patients = profile.assigned_patients.all()
            patient_ids = assigned_patients.values_list('id', flat=True)
            consented_patient_ids = Consent.objects.filter(
                doctor=user,
                patient_id__in=patient_ids,
                revoked=False,
            ).filter(
                Q(expires_at__gt=timezone.now()) | Q(expires_at__isnull=True)
            ).values_list('patient_id', flat=True)
            return MedicalReport.objects.filter(owner_id__in=consented_patient_ids)
    return MedicalReport.objects.filter(owner=user)


def get_report_for_user(user, pk):
    if hasattr(user, 'userprofile'):
        profile = user.userprofile
        if profile.is_admin or user.is_superuser:
            return get_object_or_404(MedicalReport, pk=pk)
        if profile.is_doctor:
            assigned_patients = profile.assigned_patients.all()
            patient_ids = assigned_patients.values_list('id', flat=True)
            consented_patient_ids = Consent.objects.filter(
                doctor=user,
                patient_id__in=patient_ids,
                revoked=False,
            ).filter(
                Q(expires_at__gt=timezone.now()) | Q(expires_at__isnull=True)
            ).values_list('patient_id', flat=True)
            return get_object_or_404(MedicalReport, pk=pk, owner_id__in=consented_patient_ids)
    return get_object_or_404(MedicalReport, pk=pk, owner=user)
