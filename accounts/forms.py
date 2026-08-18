from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, TeacherProfile


class TeacherRegistrationForm(UserCreationForm):

    email = forms.EmailField(required=True)
    employee_id = forms.CharField(max_length=50)
    department = forms.CharField(max_length=100)
    qualification = forms.CharField(max_length=150)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password1',
            'password2',
            'employee_id',
            'department',
            'qualification',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data['email']
        user.role = 'teacher'

        if commit:
            user.save()

            TeacherProfile.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                department=self.cleaned_data['department'],
                qualification=self.cleaned_data['qualification'],
                verification_status='pending'
            )

        return user

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(
        widget=forms.PasswordInput
    )