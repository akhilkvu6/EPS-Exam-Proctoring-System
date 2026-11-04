from django import forms
from django.forms import inlineformset_factory
from apps.question_bank.models import (
    Question,
    QuestionOption,
    QuestionCategory,
    QuestionType,
    QuestionDifficulty,
)
from apps.academics.models import Subject
from apps.academics.services.scoping import get_teacher_assigned_subjects as get_teacher_subjects


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            "subject",
            "category",
            "question_type",
            "difficulty",
            "title",
            "content",
            "image",
            "default_marks",
            "negative_marks",
            "explanation",
            "rubric",
            "numerical_target",
            "numerical_tolerance",
        ]
        widgets = {
            "subject": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "question_type": forms.Select(attrs={"class": "form-select", "id": "id_question_type"}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g., Matrix Inversion Properties"}),
            "content": forms.Textarea(attrs={"class": "form-textarea", "rows": 4, "placeholder": "Enter question content or prompt (Markdown supported)..."}),
            "image": forms.FileInput(attrs={"class": "form-file"}),
            "default_marks": forms.NumberInput(attrs={"class": "form-input", "step": "0.5"}),
            "negative_marks": forms.NumberInput(attrs={"class": "form-input", "step": "0.25"}),
            "explanation": forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "Model solution or rationale for after results publication"}),
            "rubric": forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "Grading criteria for descriptive answers"}),
            "numerical_target": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
            "numerical_tolerance": forms.NumberInput(attrs={"class": "form-input", "step": "any"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            if user.role == "TEACHER":
                teacher_subjects = get_teacher_subjects(user)
                self.fields["subject"].queryset = teacher_subjects
                self.fields["category"].queryset = QuestionCategory.objects.filter(
                    subject__in=teacher_subjects
                )
            elif user.role == "ADMIN":
                self.fields["subject"].queryset = Subject.objects.filter(is_active=True)
                self.fields["category"].queryset = QuestionCategory.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get("question_type")
        num_target = cleaned_data.get("numerical_target")

        if q_type == QuestionType.NUMERICAL and num_target is None:
            self.add_error("numerical_target", "Numerical target value is required for Numerical questions.")

        return cleaned_data


class QuestionOptionForm(forms.ModelForm):
    class Meta:
        model = QuestionOption
        fields = ["option_text", "is_correct", "order"]
        widgets = {
            "option_text": forms.TextInput(attrs={"class": "form-input", "placeholder": "Option text"}),
            "is_correct": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "style": "width: 70px;"}),
        }


QuestionOptionFormSet = inlineformset_factory(
    Question,
    QuestionOption,
    form=QuestionOptionForm,
    extra=4,
    can_delete=True,
)
