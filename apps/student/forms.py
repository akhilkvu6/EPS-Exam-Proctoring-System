"""
Student Registration and Profile Edit Forms.
Compliant with Section 8.1 (Student Registration) and Section 7 (Server-side validation).
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User, UserRole, UserStatus
from .models import StudentProfile, AdmissionApplicationStatus
import uuid


class StudentRegistrationForm(forms.Form):
    """
    Candidate institutional registration form.
    Captures essential academic application fields without paid email/SMS dependencies.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Choose a unique username"}),
        label=_("Username"),
        help_text=_("Required for signing into examinations."),
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Candidate first name"}),
        label=_("First Name"),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Candidate last name"}),
        label=_("Last Name"),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Create a strong password"}),
        label=_("Password"),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Confirm password"}),
        label=_("Confirm Password"),
    )
    department_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Department of Computer Science"}),
        label=_("Academic Department"),
    )
    course_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Bachelor of Technology (CSE)"}),
        label=_("Course / Program"),
    )
    batch_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 2024-2028"}),
        label=_("Academic Batch"),
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        label=_("Date of Birth"),
    )
    guardian_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Parent or guardian name"}),
        label=_("Guardian Full Name"),
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Contact number"}),
        label=_("Contact Number"),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with that username already exists."))
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", _("Passwords do not match."))
            else:
                validate_password(password)

        return cleaned_data

    def save(self) -> StudentProfile:
        """
        Creates User with PENDING_APPROVAL status and creates StudentProfile.
        Generates a unique registration sequence reference.
        """
        cleaned_data = self.cleaned_data
        user = User.objects.create_user(
            username=cleaned_data["username"],
            password=cleaned_data["password"],
            first_name=cleaned_data["first_name"],
            last_name=cleaned_data.get("last_name", ""),
            role=UserRole.STUDENT,
            status=UserStatus.PENDING_APPROVAL,
            phone=cleaned_data.get("contact_number"),
        )

        reg_seq = uuid.uuid4().hex[:8].upper()
        reg_number = f"APP-{reg_seq}"

        profile = StudentProfile.objects.create(
            user=user,
            registration_number=reg_number,
            department_name=cleaned_data["department_name"],
            course_name=cleaned_data["course_name"],
            batch_name=cleaned_data["batch_name"],
            date_of_birth=cleaned_data.get("date_of_birth"),
            guardian_name=cleaned_data.get("guardian_name"),
            contact_number=cleaned_data.get("contact_number"),
            admission_status=AdmissionApplicationStatus.SUBMITTED,
        )
        return profile


class StudentProfileEditForm(forms.ModelForm):
    """
    Restricted profile update form.
    Official roll numbers, admission status, and course details are read-only to prevent tampering.
    """
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label=_("First Name"),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label=_("Last Name"),
    )

    class Meta:
        model = StudentProfile
        fields = ["guardian_name", "contact_number", "date_of_birth"]
        widgets = {
            "guardian_name": forms.TextInput(attrs={"class": "form-input"}),
            "contact_number": forms.TextInput(attrs={"class": "form-input"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data.get("contact_number")
        if commit:
            user.save()
            profile.save()
        return profile
