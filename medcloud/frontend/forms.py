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
        fields = ('report_name', 'category', 'uploaded_file')

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        if not f:
            raise forms.ValidationError('No file uploaded')

        # Validate file size (limit to 10MB)
        max_size = 10 * 1024 * 1024
        if f.size > max_size:
            raise forms.ValidationError('File is too large (max 10MB)')

        # Validate file type
        valid_mime = ['application/pdf', 'image/png', 'image/jpeg']
        content_type = f.content_type
        if content_type not in valid_mime:
            raise forms.ValidationError('Unsupported file type. Allowed: PDF, PNG, JPG, JPEG')

        return f
