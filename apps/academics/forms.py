"""
Academic Management Forms for Departments, Courses, Batches, and Subjects.
"""

from django import forms
from .models import (
    Department,
    Course,
    AcademicBatch,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["code", "name", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. CSE"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Department of Computer Science"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["department", "code", "name", "duration_years", "total_semesters", "is_active"]
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. BT-CSE"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. B.Tech Computer Science"}),
            "duration_years": forms.NumberInput(attrs={"class": "form-input"}),
            "total_semesters": forms.NumberInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class AcademicBatchForm(forms.ModelForm):
    class Meta:
        model = AcademicBatch
        fields = ["course", "name", "start_year", "end_year", "current_semester", "is_active"]
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 2024-2028"}),
            "start_year": forms.NumberInput(attrs={"class": "form-input"}),
            "end_year": forms.NumberInput(attrs={"class": "form-input"}),
            "current_semester": forms.NumberInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["course", "code", "name", "semester_number", "credits", "is_active"]
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. CS201"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Data Structures"}),
            "semester_number": forms.NumberInput(attrs={"class": "form-input"}),
            "credits": forms.NumberInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class TeacherAssignmentForm(forms.ModelForm):
    class Meta:
        model = TeacherAssignment
        fields = ["teacher", "subject", "batch", "academic_year", "is_active"]
        widgets = {
            "teacher": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "batch": forms.Select(attrs={"class": "form-select"}),
            "academic_year": forms.NumberInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
