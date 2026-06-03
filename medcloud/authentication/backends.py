from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get('email')
        if identifier is None or password is None:
            return None
        identifier = identifier.strip()
        if '@' in identifier:
            identifier = identifier.lower()
        try:
            user = User.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
