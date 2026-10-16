from django import forms
from django.utils import timezone
from .models import Subject, Question, AnswerOption, Exam, ExamQuestion
from accounts.models import ClassGroup


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Database Management Systems'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BCA301'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'subject', 'question_type', 'difficulty', 'topic',
            'question_text', 'marks', 'negative_marks', 'correct_text_answer', 'explanation'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_question_type'}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Normalization, SQL Joins'}),
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter the complete question text...'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0.5'}),
            'negative_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25', 'min': '0'}),
            'correct_text_answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Expected answer keywords for reference...'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Solution explanation for students...'}),
        }


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'title', 'subject', 'description', 'instructions',
            'start_time', 'end_time', 'duration_minutes',
            'total_marks', 'passing_marks', 'negative_marking', 'default_negative_mark',
            'shuffle_questions', 'shuffle_options',
            'camera_required', 'microphone_required', 'fullscreen_required',
            'block_tab_switch', 'block_copy_paste', 'screen_sharing_required',
            'face_detection_enabled', 'max_warning_count', 'assigned_classes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BCA 3rd Sem Midterm Examination 2026'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Brief description'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '5'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'passing_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'default_negative_mark': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'camera_required': forms.Select(attrs={'class': 'form-control'}),
            'microphone_required': forms.Select(attrs={'class': 'form-control'}),
            'screen_sharing_required': forms.Select(attrs={'class': 'form-control'}),
            'max_warning_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10'}),
            'assigned_classes': forms.SelectMultiple(attrs={'class': 'form-control', 'style': 'height: 120px;'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        duration = cleaned_data.get('duration_minutes')

        if start and end:
            if end <= start:
                self.add_error('end_time', 'Examination end time must be after the start time.')
            if duration:
                window_minutes = (end - start).total_seconds() / 60
                if duration > window_minutes:
                    self.add_error('duration_minutes', f'Exam duration ({duration} mins) cannot exceed total schedule window ({int(window_minutes)} mins).')

        return cleaned_data


class RandomQuestionAddForm(forms.Form):
    count = forms.IntegerField(
        min_value=1,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of questions'})
    )
    difficulty = forms.ChoiceField(
        choices=[('any', 'Any Difficulty'), ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    topic = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by topic (optional)'})
    )
