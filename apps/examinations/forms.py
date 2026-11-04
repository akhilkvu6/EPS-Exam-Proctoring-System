from django import forms
from apps.examinations.models import Examination, ExamSection, ExamQuestion, CandidateAssignment
from apps.academics.models import Subject, AcademicBatch
from apps.academics.services.scoping import (
    get_teacher_assigned_subjects,
    get_teacher_assigned_batches,
)
from apps.question_bank.models import Question


class ExaminationForm(forms.ModelForm):
    class Meta:
        model = Examination
        fields = [
            "title",
            "code",
            "subject",
            "batch",
            "start_window",
            "end_window",
            "duration_minutes",
            "pass_percentage",
            "allow_late_join_minutes",
            "shuffle_questions",
            "shuffle_options",
            "calculator_enabled",
            "strict_proctoring",
            "instructions",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g., Mid-Term Assessment 2026"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g., EXAM-CS301-MID-2026"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "batch": forms.Select(attrs={"class": "form-select"}),
            "start_window": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "end_window": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "duration_minutes": forms.NumberInput(attrs={"class": "form-input", "min": "5"}),
            "pass_percentage": forms.NumberInput(attrs={"class": "form-input", "step": "0.5"}),
            "allow_late_join_minutes": forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
            "shuffle_questions": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "shuffle_options": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "calculator_enabled": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "strict_proctoring": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "instructions": forms.Textarea(attrs={"class": "form-textarea", "rows": 4, "placeholder": "Institutional rules..."}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            if user.role == "TEACHER":
                self.fields["subject"].queryset = get_teacher_assigned_subjects(user)
                self.fields["batch"].queryset = get_teacher_assigned_batches(user)
            elif user.role == "ADMIN":
                self.fields["subject"].queryset = Subject.objects.filter(is_active=True)
                self.fields["batch"].queryset = AcademicBatch.objects.filter(is_active=True)


class ExamSectionForm(forms.ModelForm):
    class Meta:
        model = ExamSection
        fields = ["title", "order", "instructions"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g., Part 1: Multiple Choice"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": "1"}),
            "instructions": forms.Textarea(attrs={"class": "form-textarea", "rows": 2}),
        }


class AddQuestionToSectionForm(forms.Form):
    question = forms.ModelChoiceField(
        queryset=Question.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    marks = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.5", "placeholder": "Default if blank"}),
    )
    negative_marks = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.25", "placeholder": "Default if blank"}),
    )

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", None)
        super().__init__(*args, **kwargs)
        if subject:
            self.fields["question"].queryset = Question.objects.filter(
                subject=subject,
                is_archived=False,
            ).select_related("category")
