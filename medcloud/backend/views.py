import json
import re
from pathlib import Path
from django.http import Http404, JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import PatientProfile, Appointment, Medication, Report

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {
    '.pdf': b'%PDF-',
    '.png': b'\x89PNG\r\n\x1a\n',
    '.jpg': b'\xff\xd8\xff',
    '.jpeg': b'\xff\xd8\xff',
}


def _sanitize_filename(filename):
    safe_name = Path(filename).name
    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', safe_name)
    return safe_name or 'report'


def _is_valid_magic_bytes(header: bytes, extension: str) -> bool:
    expected = ALLOWED_UPLOAD_EXTENSIONS.get(extension)
    if not expected:
        return False
    return header.startswith(expected)


def _validate_uploaded_file(f):
    if not f:
        raise ValueError('no file provided')

    if f.size > MAX_UPLOAD_SIZE:
        raise ValueError('file is too large; max 10MB allowed.')

    filename = getattr(f, 'name', '')
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError('Unsupported file extension.')

    header = f.read(16)
    f.seek(0)
    if not _is_valid_magic_bytes(header, extension):
        raise ValueError('File content does not match its declared type.')


def _get_patient_for_request(request, patient_name=None):
    if request.user.is_staff:
        if not patient_name:
            raise ValueError('patient is required for staff actions')
        patient, _ = PatientProfile.objects.get_or_create(full_name=patient_name)
        return patient

    profile = getattr(request.user, 'patientprofile', None)
    if profile is None:
        profile = PatientProfile.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
        )
    return profile


def _serialize_appointment(item):
    return {
        'id': item.id,
        'patient': item.patient.full_name,
        'scheduled_at': item.scheduled_at.isoformat(),
        'reason': item.reason,
        'status': item.status,
    }


def _serialize_medication(item):
    return {
        'id': item.id,
        'patient': item.patient.full_name,
        'name': item.name,
        'dosage': item.dosage,
        'frequency': item.frequency,
    }


def _serialize_report(item):
    return {
        'id': item.id,
        'patient': item.patient.full_name,
        'title': item.title,
        'file_url': item.file.url if item.file else None,
        'uploaded_at': item.uploaded_at.isoformat(),
    }


@login_required
@require_http_methods(['GET'])
def appointments_list(request):
    if request.user.is_staff:
        items = Appointment.objects.select_related('patient').all().order_by('-scheduled_at')
    else:
        items = Appointment.objects.select_related('patient').filter(patient__user=request.user).order_by('-scheduled_at')
    return JsonResponse({'appointments': [_serialize_appointment(item) for item in items]})


@login_required
@require_http_methods(['POST'])
def appointments_create(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Only staff may create appointments.')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    patient_name = payload.get('patient')
    if not patient_name:
        return JsonResponse({'error': 'patient field is required.'}, status=400)

    patient = _get_patient_for_request(request, patient_name)
    if not payload.get('scheduled_at'):
        return JsonResponse({'error': 'scheduled_at field is required.'}, status=400)

    appt = Appointment.objects.create(
        patient=patient,
        scheduled_at=payload.get('scheduled_at'),
        reason=payload.get('reason', ''),
        status=payload.get('status', 'scheduled'),
    )
    return JsonResponse({'id': appt.id})


@login_required
@require_http_methods(['GET'])
def medications_list(request):
    if request.user.is_staff:
        items = Medication.objects.select_related('patient').all()
    else:
        items = Medication.objects.select_related('patient').filter(patient__user=request.user)
    return JsonResponse({'medications': [_serialize_medication(item) for item in items]})


@login_required
@require_http_methods(['POST'])
def medications_create(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Only staff may create medication entries.')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    patient_name = payload.get('patient')
    if not patient_name:
        return JsonResponse({'error': 'patient field is required.'}, status=400)

    if not payload.get('name'):
        return JsonResponse({'error': 'name field is required.'}, status=400)

    patient = _get_patient_for_request(request, patient_name)
    med = Medication.objects.create(
        patient=patient,
        name=payload.get('name'),
        dosage=payload.get('dosage', ''),
        frequency=payload.get('frequency', ''),
    )
    return JsonResponse({'id': med.id})


@login_required
@require_http_methods(['GET'])
def reports_list(request):
    if request.user.is_staff:
        items = Report.objects.select_related('patient').all().order_by('-uploaded_at')
    else:
        items = Report.objects.select_related('patient').filter(patient__user=request.user).order_by('-uploaded_at')
    return JsonResponse({'reports': [_serialize_report(item) for item in items]})


@login_required
@require_http_methods(['POST'])
def upload_report(request):
    return HttpResponseForbidden('Legacy upload endpoint is disabled. Use the secure frontend upload workflow.')
