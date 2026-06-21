from pathlib import Path

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import UserProfile, MedicalReport

User = get_user_model()


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone', 'dob', 'blood_group', 'address')


class MedicalReportForm(forms.ModelForm):
    class Meta:
        model = MedicalReport
        fields = ('report_name', 'category', 'encrypted_file')

    def clean_encrypted_file(self):
        f = self.cleaned_data.get('encrypted_file')
        if not f:
            raise forms.ValidationError('No file uploaded')

        # Validate file size (limit to 10MB)
        max_size = 10 * 1024 * 1024
        if f.size > max_size:
            raise forms.ValidationError('File is too large (max 10MB)')

        # Validate file extension
        allowed_extensions = ['.pdf', '.png', '.jpg', '.jpeg']
        filename = getattr(f, 'name', '')
        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            raise forms.ValidationError('Unsupported file extension. Allowed: PDF, PNG, JPG, JPEG')

        # Validate magic bytes instead of trusting MIME type
        header = f.read(16)
        f.seek(0)
        if not self._is_valid_magic_bytes(header, ext):
            raise forms.ValidationError('File content does not match its declared type.')

        return f

    @staticmethod
    def _is_valid_magic_bytes(header: bytes, extension: str) -> bool:
        if extension == '.pdf':
            return header.startswith(b'%PDF-')
        if extension == '.png':
            return header.startswith(b'\x89PNG\r\n\x1a\n')
        if extension in ('.jpg', '.jpeg'):
            return header.startswith(b'\xff\xd8\xff')
        return False
