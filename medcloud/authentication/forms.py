from django import forms
from .models import User


class GoogleSocialSignupForm(forms.Form):
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label='Select your role',
    )
    username = forms.CharField(max_length=150, required=False, label='Username')
    first_name = forms.CharField(max_length=150, required=False, label='First name')
    last_name = forms.CharField(max_length=150, required=False, label='Last name')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request is not None:
            role = request.session.get('google_auth_role')
            if role in [User.ROLE_PATIENT, User.ROLE_DOCTOR]:
                self.fields['role'].initial = role
                self.fields['role'].widget = forms.HiddenInput()

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in [User.ROLE_PATIENT, User.ROLE_DOCTOR]:
            raise forms.ValidationError('Role selection is required.')
        return role
