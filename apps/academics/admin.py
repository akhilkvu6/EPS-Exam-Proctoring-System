"""
Django admin integration for apps.academics models.
"""

from django.contrib import admin
from .models import (
    Department,
    Course,
    AcademicBatch,
    Semester,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "duration_years", "total_semesters", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("code", "name")


@admin.register(AcademicBatch)
class AcademicBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "start_year", "end_year", "current_semester", "is_active")
    list_filter = ("course", "is_active")


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("batch", "semester_number", "is_current")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "course", "semester_number", "credits", "is_active")
    list_filter = ("course", "semester_number", "is_active")
    search_fields = ("code", "name")


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "subject", "batch", "academic_year", "is_active")
    list_filter = ("academic_year", "is_active")


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "batch", "current_semester", "status")
    list_filter = ("status", "current_semester")
