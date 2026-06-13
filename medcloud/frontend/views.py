from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, FormView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from .forms import UserRegistrationForm, MedicalReportForm, ProfileForm, LoginForm
from .models import MedicalReport, Appointment, Medication, Subscription, UserProfile
from django.contrib.auth import login


class LandingPageView(TemplateView):
    template_name = 'index.html'


class LoginView(AuthLoginView):
    template_name = 'login.html'
    authentication_form = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        return super().form_valid(form)


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('landing')


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
        ctx['total_reports'] = MedicalReport.objects.filter(patient=user).count()
        ctx['total_appointments'] = Appointment.objects.filter(patient=user).count()
        ctx['active_medications'] = Medication.objects.filter(patient=user).count()
        # Subscription status (simple latest)
        subscription = Subscription.objects.filter(user=user).order_by('-start_date').first()
        ctx['subscription'] = subscription
        ctx['recent_reports'] = MedicalReport.objects.filter(patient=user).order_by('-upload_date')[:5]
        ctx['upcoming_appointments'] = Appointment.objects.filter(patient=user).order_by('appointment_date')[:5]
        ctx['medications'] = Medication.objects.filter(patient=user)[:5]
        return ctx


class UploadView(LoginRequiredMixin, FormView):
    template_name = 'upload.html'
    form_class = MedicalReportForm
    success_url = reverse_lazy('upload')

    def form_valid(self, form):
        report = form.save(commit=False)
        report.patient = self.request.user
        report.save()
        messages.success(self.request, 'Report uploaded successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_reports'] = MedicalReport.objects.filter(patient=self.request.user).order_by('-upload_date')[:5]
        return ctx


class ReportsListView(LoginRequiredMixin, ListView):
    template_name = 'reports.html'
    model = MedicalReport
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        qs = MedicalReport.objects.filter(patient=self.request.user).order_by('-upload_date')
        q = self.request.GET.get('q')
        category = self.request.GET.get('category')
        if q:
            qs = qs.filter(report_name__icontains=q)
        if category:
            qs = qs.filter(category=category)
        return qs


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = MedicalReport
    template_name = 'report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return MedicalReport.objects.filter(patient=self.request.user)


class ReportDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)
        report.uploaded_file.delete(save=False)
        report.delete()
        messages.success(request, 'Report deleted successfully.')
        return redirect('reports')


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