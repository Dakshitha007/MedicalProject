from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, OTPVerification
from patients.models import PatientProfile
from doctors.models import DoctorProfile


@receiver(post_save, sender=User)
def create_profiles(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.role == User.ROLE_PATIENT:
        PatientProfile.objects.get_or_create(user=instance)
    elif instance.role == User.ROLE_DOCTOR:
        DoctorProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=OTPVerification)
def deactivate_expired_otps(sender, instance, **kwargs):
    if instance.is_verified:
        return
    if instance.is_expired():
        instance.delete()
