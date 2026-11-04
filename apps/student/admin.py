"""
Django admin integration for StudentProfile.
"""

from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "registration_number",
        "roll_number",
        "department_name",
        "course_name",
        "current_semester",
        "admission_status",
    )
    list_filter = ("admission_status", "current_semester", "department_name")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "registration_number",
        "roll_number",
    )
    readonly_fields = ("created_at", "updated_at")
