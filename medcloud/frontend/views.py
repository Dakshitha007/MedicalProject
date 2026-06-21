import os
import re
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, FormView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth import login

from .forms import UserRegistrationForm, MedicalReportForm, ProfileForm, LoginForm
from .models import MedicalReport, Appointment, Medication, Subscription, UserProfile, BlockchainRecord
from .services.report_verification import verify_report_integrity
from .utils import log_audit, get_report_for_user, get_accessible_reports
import hash_service
from services.encryption_service import decrypt_file, encrypt_file
from blockchain.blockchain_service import add_report_hash, get_chain_summary, get_report_history, verify_report_hash


def _sanitize_filename(filename: str) -> str:
    safe_name = os.path.basename(filename)
    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', safe_name)
    return safe_name or 'report'


def _get_safe_media_path(path_candidate: Path) -> Path:
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if not path_candidate.is_absolute():
        path_candidate = media_root / path_candidate
    resolved_path = path_candidate.resolve()
    if not resolved_path.is_relative_to(media_root):
        raise ValueError('Invalid media storage path')
    return resolved_path


class LandingPageView(TemplateView):
    template_name = 'index.html'


class LoginView(AuthLoginView):
    template_name = 'login.html'
    authentication_form = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        response = super().form_valid(form)
        log_audit(self.request.user, 'login', request=self.request, details='User logged in')
        return response


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('landing')

    def dispatch(self, request, *args, **kwargs):
        user = request.user if request.user.is_authenticated else None
        response = super().dispatch(request, *args, **kwargs)
        if user:
            log_audit(user, 'logout', request=request, details='User logged out')
        return response


class RegistrationView(FormView):
    template_name = 'registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        # Create empty profile
        UserProfile.objects.get_or_create(user=user)
        login(self.request, user)
        messages.success(self.request, 'Registration successful. Welcome!')
        return super().form_valid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        reports = get_accessible_reports(user)
        ctx['total_reports'] = reports.count()
        ctx['verified_reports'] = reports.filter(verification_status='verified').count()
        ctx['pending_reports'] = reports.filter(verification_status='pending').count()
        ctx['tampered_reports'] = reports.filter(verification_status='tampered').count()
        ctx['total_appointments'] = Appointment.objects.filter(patient=user).count()
        ctx['active_medications'] = Medication.objects.filter(patient=user).count()
        subscription = Subscription.objects.filter(user=user).order_by('-start_date').first()
        ctx['subscription'] = subscription
        ctx['recent_reports'] = reports.order_by('-upload_date')[:5]
        ctx['upcoming_appointments'] = Appointment.objects.filter(patient=user).order_by('appointment_date')[:5]
        ctx['medications'] = Medication.objects.filter(patient=user)[:5]
        return ctx


class UploadView(LoginRequiredMixin, FormView):
    template_name = 'upload.html'
    form_class = MedicalReportForm
    success_url = reverse_lazy('upload')

    def form_valid(self, form):
        uploaded_file = form.cleaned_data['encrypted_file']
        original_name = _sanitize_filename(uploaded_file.name)

        # write the uploaded plaintext to a temp file for hashing and encryption
        temp_path = None
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            temp_file.write(uploaded_file.read())
            temp_file.flush()
            temp_path = Path(temp_file.name)
        finally:
            temp_file.close()

        original_hash = hash_service.file_sha256(temp_path)
        report_name = form.cleaned_data['report_name']
        category = form.cleaned_data['category']

        # encrypt the plaintext temp file and store encrypted version
        encrypted_filename = f'{uuid.uuid4().hex}_{original_name}'
        encrypted_path = _get_safe_media_path(Path('reports') / 'encrypted' / encrypted_filename)
        encryption_meta = encrypt_file(temp_path, encrypted_path)
        temp_path.unlink(missing_ok=True)

        encrypted_hash = hash_service.file_sha256(encrypted_path)

        report = MedicalReport(
            owner=self.request.user,
            report_name=report_name,
            category=category,
            original_filename=original_name,
            file_hash=original_hash,
            hash_value=encrypted_hash,
            verification_status='pending',
            encryption_metadata=encryption_meta,
        )
        report.encrypted_file.name = str(encrypted_path.relative_to(Path(settings.MEDIA_ROOT).resolve())).replace('\\', '/')

        blockchain_record_data = None
        try:
            with transaction.atomic():
                report.save()
                blockchain_record_data = add_report_hash(encrypted_hash, report.id, self.request.user.id)
                bc = BlockchainRecord.objects.create(
                    report=report,
                    report_hash=encrypted_hash,
                    transaction_reference=blockchain_record_data['txid'],
                    block_timestamp=timezone.make_aware(timezone.datetime.fromtimestamp(blockchain_record_data['timestamp'])),
                    verification_status='pending',
                )

                verification = verify_report_integrity(report)
                if verification.get('local_match') and verification.get('blockchain_match') and verification.get('chain_valid'):
                    report.verification_status = 'verified'
                    bc.verification_status = 'verified'
                    messages.success(self.request, 'Report uploaded, encrypted, and verified successfully.')
                else:
                    report.verification_status = 'tampered'
                    bc.verification_status = 'tampered'
                    if verification.get('chain_valid') is False:
                        messages.error(self.request, 'Report upload blocked because blockchain ledger integrity failed. Upload aborted.')
                        raise RuntimeError('Blockchain ledger integrity failed during upload.')
                    elif verification.get('blockchain_match') is False:
                        messages.warning(self.request, 'Report uploaded, but blockchain audit record does not match the stored report hash.')
                    else:
                        messages.warning(self.request, 'Report uploaded, but integrity verification failed.')

                report.blockchain_txid = blockchain_record_data['txid']
                report.block_number = blockchain_record_data['block_number']
                report.save()
                bc.save()
                log_audit(self.request.user, 'upload', request=self.request, report=report, details='Report uploaded and processed')
                return super().form_valid(form)
        except RuntimeError as exc:
            report_id = getattr(report, 'id', None)
            if report_id:
                MedicalReport.objects.filter(id=report_id).delete()
            if encrypted_path.exists():
                try:
                    encrypted_path.unlink()
                except Exception:
                    pass
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        except Exception:
            report_id = getattr(report, 'id', None)
            if report_id:
                MedicalReport.objects.filter(id=report_id).delete()
            if encrypted_path.exists():
                try:
                    encrypted_path.unlink()
                except Exception:
                    pass
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_reports'] = MedicalReport.objects.filter(owner=self.request.user).order_by('-upload_date')[:5]
        return ctx


class ReportsListView(LoginRequiredMixin, ListView):
    template_name = 'reports.html'
    model = MedicalReport
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        qs = get_accessible_reports(self.request.user).order_by('-upload_date')
        q = self.request.GET.get('q')
        category = self.request.GET.get('category')
        if q:
            qs = qs.filter(report_name__icontains=q)
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['verified_reports'] = self.get_queryset().filter(verification_status='verified').count()
        ctx['pending_reports'] = self.get_queryset().filter(verification_status='pending').count()
        ctx['tampered_reports'] = self.get_queryset().filter(verification_status='tampered').count()
        return ctx


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = MedicalReport
    template_name = 'report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return get_accessible_reports(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['integrity'] = verify_report_integrity(self.object)
        return ctx


class ReportVerificationView(LoginRequiredMixin, View):
    def get(self, request, pk):
        report = get_report_for_user(request.user, pk)
        verification = verify_report_integrity(report)
        bc = verification.get('blockchain_record')

        chain_valid = verification.get('chain_valid') is not False
        if verification.get('local_match') and verification.get('blockchain_match') and chain_valid:
            report.verification_status = 'verified'
            if bc:
                bc.verification_status = 'verified'
                bc.save()
            messages.success(request, 'Report integrity verified successfully.')
        else:
            report.verification_status = 'tampered'
            if bc:
                bc.verification_status = 'tampered'
                bc.save()
            if verification.get('chain_valid') is False:
                messages.warning(request, 'Report verification failed because the blockchain ledger integrity is invalid.')
            elif verification.get('blockchain_match') is False:
                messages.warning(request, 'Report verification failed because the blockchain audit record did not match the report hash.')
            else:
                messages.warning(request, 'Report integrity verification failed. Review blockchain audit and report contents.')

        report.save()
        log_audit(request.user, 'verify', request=request, report=report, details='Report integrity rechecked')
        return redirect('report_detail', pk=report.pk)


class BlockchainStatusView(LoginRequiredMixin, TemplateView):
    template_name = 'blockchain_status.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['summary'] = get_chain_summary()
        ctx['latest_blocks'] = BlockchainRecord.objects.order_by('-block_timestamp')[:10]
        report_id = self.request.GET.get('report_id')
        try:
            report_id = int(report_id) if report_id else None
        except (TypeError, ValueError):
            report_id = None
        ctx['report_history'] = get_report_history(report_id) if report_id else []
        return ctx


class ReportDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        report = get_report_for_user(request.user, pk)
        try:
            _get_safe_media_path(Path(report.encrypted_file.name))
        except ValueError:
            raise Http404('Encrypted report not found')

        report.encrypted_file.delete(save=False)
        report.delete()
        log_audit(request.user, 'delete', request=request, report=report, details='Report deleted')
        messages.success(request, 'Report deleted successfully.')
        return redirect('reports')


class ReportDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        report = get_report_for_user(request.user, pk)
        try:
            file_path = _get_safe_media_path(Path(report.encrypted_file.name))
        except ValueError:
            raise Http404('Encrypted report not found')
        if not file_path.exists():
            raise Http404('Encrypted report not found')

        file_handle = file_path.open('rb')
        response = FileResponse(file_handle, as_attachment=True, filename=_sanitize_filename(report.original_filename))

        original_close = response.close
        def close_and_cleanup():
            try:
                original_close()
            finally:
                try:
                    if not file_handle.closed:
                        file_handle.close()
                except Exception:
                    pass
        response.close = close_and_cleanup

        log_audit(request.user, 'download', request=request, report=report, details='Report downloaded')
        return response


class SecureReportDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        report = get_report_for_user(request.user, pk)
        try:
            encrypted_path = _get_safe_media_path(Path(report.encrypted_file.name))
        except ValueError:
            raise Http404('Encrypted report not found')
        if not encrypted_path.exists():
            raise Http404('Encrypted report not found')

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                decrypt_file(encrypted_path, metadata=report.encryption_metadata or {}, output_path=temp_path)

            file_handle = temp_path.open('rb')
            response = FileResponse(file_handle, as_attachment=True, filename=_sanitize_filename(report.original_filename))

            original_close = response.close
            def close_and_cleanup():
                try:
                    original_close()
                finally:
                    try:
                        if temp_path and temp_path.exists():
                            temp_path.unlink()
                    except Exception:
                        pass
            response.close = close_and_cleanup

            log_audit(request.user, 'secure_download', request=request, report=report, details='Secure report download')
            return response
        except Exception as exc:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise Http404('Unable to decrypt report') from exc


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'setting.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        ctx['profile_form'] = ProfileForm(instance=profile)
        return ctx

    def post(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('setting')
        messages.error(request, 'Please fix the errors below.')
        return render(request, self.template_name, {'profile_form': form})