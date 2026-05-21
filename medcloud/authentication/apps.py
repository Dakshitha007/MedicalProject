from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        # Import signals to attach OTP cleanup and profile creation
        from . import signals  # noqa: F401
