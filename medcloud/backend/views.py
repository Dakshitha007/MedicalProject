from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import PatientProfile, Appointment, Medication, Report
import json


def _model_to_dict(instance, fields):
	data = {}
	for f in fields:
		data[f] = getattr(instance, f)
	return data


def appointments_list(request):
	items = Appointment.objects.select_related('patient').all().order_by('-scheduled_at')
	data = []
	for it in items:
		data.append({
			'id': it.id,
			'patient': it.patient.full_name,
			'scheduled_at': it.scheduled_at.isoformat(),
			'reason': it.reason,
			'status': it.status,
		})
	return JsonResponse({'appointments': data})


@csrf_exempt
@require_http_methods(['POST'])
def appointments_create(request):
	payload = json.loads(request.body.decode('utf-8'))
	patient_name = payload.get('patient')
	patient, _ = PatientProfile.objects.get_or_create(full_name=patient_name)
	appt = Appointment.objects.create(
		patient=patient,
		scheduled_at=payload.get('scheduled_at'),
		reason=payload.get('reason', ''),
		status=payload.get('status', 'scheduled')
	)
	return JsonResponse({'id': appt.id})


def medications_list(request):
	items = Medication.objects.select_related('patient').all()
	data = []
	for it in items:
		data.append({
			'id': it.id,
			'patient': it.patient.full_name,
			'name': it.name,
			'dosage': it.dosage,
			'frequency': it.frequency,
		})
	return JsonResponse({'medications': data})


@csrf_exempt
@require_http_methods(['POST'])
def medications_create(request):
	payload = json.loads(request.body.decode('utf-8'))
	patient_name = payload.get('patient')
	patient, _ = PatientProfile.objects.get_or_create(full_name=patient_name)
	med = Medication.objects.create(
		patient=patient,
		name=payload.get('name'),
		dosage=payload.get('dosage', ''),
		frequency=payload.get('frequency', ''),
	)
	return JsonResponse({'id': med.id})


def reports_list(request):
	items = Report.objects.select_related('patient').all().order_by('-uploaded_at')
	data = []
	for it in items:
		data.append({
			'id': it.id,
			'patient': it.patient.full_name,
			'title': it.title,
			'file_url': it.file.url if it.file else None,
			'uploaded_at': it.uploaded_at.isoformat(),
		})
	return JsonResponse({'reports': data})


@csrf_exempt
@require_http_methods(['POST'])
def upload_report(request):
	# expects multipart/form-data with fields: patient, title, file
	patient_name = request.POST.get('patient') or 'Unknown'
	title = request.POST.get('title') or 'Report'
	patient, _ = PatientProfile.objects.get_or_create(full_name=patient_name)
	f = request.FILES.get('file')
	if not f:
		return JsonResponse({'error': 'no file provided'}, status=400)
	rep = Report.objects.create(patient=patient, title=title, file=f)
	return JsonResponse({'id': rep.id, 'file_url': rep.file.url})
