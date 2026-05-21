from django.http import JsonResponse


class RoleAuthorizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.doctor_paths = ['/api/reports/', '/api/doctors/', '/api/dashboard/doctor/', '/api/appointments/']
        self.patient_paths = ['/api/patients/', '/api/dashboard/patient/', '/api/appointments/', '/api/reports/']

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path
        if path.startswith('/api/doctors/') and user and user.is_authenticated and user.role != 'DOCTOR' and not user.is_staff:
            return JsonResponse({'detail': 'Forbidden: doctor access only.'}, status=403)
        if path.startswith('/api/patients/') and user and user.is_authenticated and user.role != 'PATIENT':
            return JsonResponse({'detail': 'Forbidden: patient access only.'}, status=403)
        return self.get_response(request)
