from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, TeacherProfile, StudentProfile


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


class StudentRegistrationForm(UserCreationForm):

    email = forms.EmailField(required=True)
    roll_number = forms.CharField(max_length=50)
    department = forms.CharField(max_length=100)
    semester = forms.CharField(max_length=20)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password1',
            'password2',
            'roll_number',
            'department',
            'semester',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data['email']
        user.role = 'student'

        if commit:
            user.save()

            StudentProfile.objects.create(
                user=user,
                roll_number=self.cleaned_data['roll_number'],
                department=self.cleaned_data['department'],
                semester=self.cleaned_data['semester']
            )

        return user