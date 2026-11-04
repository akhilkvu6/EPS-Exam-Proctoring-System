"""
Teacher Workspace Forms for Profile and Admission Review.
Compliant with Section 8.3 (Teacher workflow).
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import TeacherProfile, AdmissionReviewRecord, AdmissionReviewAction


class TeacherProfileEditForm(forms.ModelForm):
    """
    Profile update form for faculty members.
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
        model = TeacherProfile
        fields = ["designation", "office_location", "qualifications"]
        widgets = {
            "designation": forms.TextInput(attrs={"class": "form-input"}),
            "office_location": forms.TextInput(attrs={"class": "form-input"}),
            "qualifications": forms.TextInput(attrs={"class": "form-input"}),
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
        if commit:
            user.save()
            profile.save()
        return profile


class AdmissionReviewForm(forms.ModelForm):
    """
    Faculty admission review decision form.
    Allows approving, rejecting, requesting info, or escalating to institutional admin.
    """
    action = forms.ChoiceField(
        choices=AdmissionReviewAction.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Review Decision"),
    )
    remarks = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Provide institutional justification, instructions, or internal remarks...",
            }
        ),
        label=_("Official Remarks / Notes"),
        help_text=_("Required for all decisions to maintain institutional audit compliance."),
    )
    roll_number = forms.CharField(
        max_length=64,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "e.g. CS-2026-0001 (or leave blank to auto-allocate)",
            }
        ),
        label=_("Assign Roll Number (Optional Override)"),
        help_text=_("Only applied if decision is 'Approve Admission Application'."),
    )

    class Meta:
        model = AdmissionReviewRecord
        fields = ["action", "remarks"]
