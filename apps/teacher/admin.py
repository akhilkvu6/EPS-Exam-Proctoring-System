"""
Django admin integration for apps.teacher models.
"""

from django.contrib import admin
from .models import TeacherProfile, AdmissionReviewRecord


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "staff_id",
        "designation",
        "department_name",
        "is_head_of_department",
    )
    list_filter = ("department_name", "is_head_of_department")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "staff_id",
        "department_name",
    )


@admin.register(AdmissionReviewRecord)
class AdmissionReviewRecordAdmin(admin.ModelAdmin):
    list_display = (
        "student_profile",
        "reviewer",
        "action",
        "created_at",
    )
    list_filter = ("action", "created_at")
    search_fields = (
        "student_profile__registration_number",
        "student_profile__user__username",
        "reviewer__username",
        "remarks",
    )
