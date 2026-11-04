"""
Administration Forms for Settings, User Governance, and Escalation Decisions.
Compliant with Section 8.4 and Section 21.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.teacher.models import TeacherProfile
from .models import InstitutionSetting


class InstitutionSettingsForm(forms.ModelForm):
    """
    Form for configuring institutional branding, theme defaults, and admission policies.
    """
    class Meta:
        model = InstitutionSetting
        fields = [
            "institution_name",
            "tagline",
            "contact_email",
            "contact_phone",
            "default_theme",
            "default_accent_color",
            "allow_student_self_registration",
            "roll_number_prefix",
        ]
        widgets = {
            "institution_name": forms.TextInput(attrs={"class": "form-input"}),
            "tagline": forms.TextInput(attrs={"class": "form-input"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-input"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-input"}),
            "default_theme": forms.Select(attrs={"class": "form-select"}),
            "default_accent_color": forms.TextInput(attrs={"class": "form-input", "type": "color"}),
            "roll_number_prefix": forms.TextInput(attrs={"class": "form-input"}),
            "allow_student_self_registration": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class TeacherCreateForm(forms.Form):
    """
    Admin provisioning form for new faculty accounts.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. prof_anderson"}),
        label=_("Faculty Username"),
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label=_("First Name"),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label=_("Last Name"),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
        label=_("Temporary Password"),
    )
    staff_id = forms.CharField(
        max_length=64,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. FAC-CS-0042"}),
        label=_("Official Staff Identifier"),
    )
    department_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Department of Computer Science"}),
        label=_("Academic Department"),
    )
    designation = forms.CharField(
        max_length=100,
        initial="Assistant Professor",
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label=_("Academic Designation"),
    )
    office_location = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input"}),
        label=_("Office / Room"),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with this username already exists."))
        return username

    def clean_staff_id(self):
        staff_id = self.cleaned_data["staff_id"].strip()
        if TeacherProfile.objects.filter(staff_id__iexact=staff_id).exists():
            raise forms.ValidationError(_("A faculty member with this staff identifier already exists."))
        return staff_id

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self) -> TeacherProfile:
        cleaned_data = self.cleaned_data
        user = User.objects.create_user(
            username=cleaned_data["username"],
            password=cleaned_data["password"],
            first_name=cleaned_data["first_name"],
            last_name=cleaned_data["last_name"],
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_verified=True,
        )
        profile = TeacherProfile.objects.create(
            user=user,
            staff_id=cleaned_data["staff_id"],
            department_name=cleaned_data["department_name"],
            designation=cleaned_data["designation"],
            office_location=cleaned_data.get("office_location"),
        )
        return profile


class AdminEscalationDecisionForm(forms.Form):
    """
    Form for institutional admin resolving escalated admission exceptions.
    Section 8.4: Approve, Reject, or Return for More Information.
    """
    DECISION_CHOICES = [
        ("APPROVE", _("Approve Admission & Allocate Roll Number")),
        ("REJECT", _("Reject Application")),
        ("RETURN", _("Return to Department Faculty for More Information")),
    ]

    action = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Administrative Determination"),
    )
    remarks = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "State institutional justification or instructions...",
            }
        ),
        label=_("Administrative Remarks"),
    )
    roll_number = forms.CharField(
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Custom roll number (optional)"}),
        label=_("Official Roll Number Override"),
        help_text=_("If left blank on approval, sequential roll format will be generated."),
    )
