from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import AuditLog, MedicalReport


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit(user, action, request=None, report=None, details=None):
    audit = AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request) if request else None,
        report=report,
        details=details,
    )
    return audit


def get_accessible_reports(user):
    if hasattr(user, 'userprofile'):
        profile = user.userprofile
        if profile.is_admin or user.is_superuser:
            return MedicalReport.objects.all()
        if profile.is_doctor:
            assigned_patients = profile.assigned_patients.all()
            return MedicalReport.objects.filter(owner__in=assigned_patients)
    return MedicalReport.objects.filter(owner=user)


def get_report_for_user(user, pk):
    if hasattr(user, 'userprofile'):
        profile = user.userprofile
        if profile.is_admin or user.is_superuser:
            return get_object_or_404(MedicalReport, pk=pk)
        if profile.is_doctor:
            assigned_patients = profile.assigned_patients.all()
            return get_object_or_404(MedicalReport, pk=pk, owner__in=assigned_patients)
    return get_object_or_404(MedicalReport, pk=pk, owner=user)
