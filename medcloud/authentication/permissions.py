from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'DOCTOR')


class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'PATIENT')


class IsDoctorVerified(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or request.user.role != 'DOCTOR':
            return False
        doctor_profile = getattr(request.user, 'doctorprofile', None)
        return bool(doctor_profile and doctor_profile.verification_status == 'approved' and doctor_profile.is_doctor_verified)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))


class AllowAnyAuthenticatedWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
