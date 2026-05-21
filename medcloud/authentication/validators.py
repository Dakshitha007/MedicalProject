import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ComplexPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(_('Password must contain at least 8 characters.'), code='password_too_short')
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_('Password must contain at least one uppercase letter.'), code='password_no_upper')
        if not re.search(r'[a-z]', password):
            raise ValidationError(_('Password must contain at least one lowercase letter.'), code='password_no_lower')
        if not re.search(r'[0-9]', password):
            raise ValidationError(_('Password must contain at least one number.'), code='password_no_number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_('Password must contain at least one special character.'), code='password_no_special')
        forbidden = ['123456', 'password']
        if user is not None:
            username = getattr(user, 'username', '') or ''
            email_name = getattr(user, 'email', '').split('@')[0]
            forbidden.extend([username.lower(), email_name.lower()])
        lowered = password.lower()
        for token in forbidden:
            if token and token in lowered:
                raise ValidationError(_('Password cannot contain personal data or common sequences.'), code='password_too_common')

    def get_help_text(self):
        return _(
            'Your password must be at least 8 characters long, include uppercase and lowercase letters, a number, and a special character. '
            'It cannot contain your username, email prefix, 123456, or password.'
        )
