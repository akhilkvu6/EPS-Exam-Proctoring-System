"""
Academic Structure Views for EPS Phoenix.
Compliant with Section 9 (Academic management and scoping).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.decorators import teacher_required, admin_required
from .models import (
    Department,
    Course,
    AcademicBatch,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)
from .forms import (
    DepartmentForm,
    CourseForm,
    AcademicBatchForm,
    SubjectForm,
    TeacherAssignmentForm,
)


@teacher_required
def departments_list_view(request):
    """List all institutional academic departments."""
    departments = Department.objects.all().order_by("name")
    form = DepartmentForm()

    if request.method == "POST" and request.user.is_staff:
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created successfully.")
            return redirect("academics:departments_list")

    context = {
        "title": "Academic Departments",
        "departments": departments,
        "form": form,
    }
    return render(request, "academics/departments_list.html", context)


@teacher_required
def courses_list_view(request):
    """List courses with parent departments."""
    courses = Course.objects.select_related("department").all().order_by("department", "name")
    form = CourseForm()

    if request.method == "POST" and request.user.is_staff:
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course program created successfully.")
            return redirect("academics:courses_list")

    context = {
        "title": "Academic Degree Programs",
        "courses": courses,
        "form": form,
    }
    return render(request, "academics/courses_list.html", context)


@teacher_required
def batches_list_view(request):
    """List graduating academic cohorts / batches."""
    batches = AcademicBatch.objects.select_related("course__department").all().order_by("-start_year")
    form = AcademicBatchForm()

    if request.method == "POST" and request.user.is_staff:
        form = AcademicBatchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic batch cohort created successfully.")
            return redirect("academics:batches_list")

    context = {
        "title": "Academic Batches",
        "batches": batches,
        "form": form,
    }
    return render(request, "academics/batches_list.html", context)


@teacher_required
def subjects_list_view(request):
    """List curriculum subjects / papers."""
    subjects = Subject.objects.select_related("course").all().order_by("course", "semester_number", "code")
    form = SubjectForm()

    if request.method == "POST" and request.user.is_staff:
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Curriculum subject created successfully.")
            return redirect("academics:subjects_list")

    context = {
        "title": "Curriculum Subjects",
        "subjects": subjects,
        "form": form,
    }
    return render(request, "academics/subjects_list.html", context)


@admin_required
def teacher_assignments_view(request):
    """Admin management of faculty scoping assignments."""
    assignments = TeacherAssignment.objects.select_related("teacher", "subject", "batch").all()
    form = TeacherAssignmentForm()

    if request.method == "POST":
        form = TeacherAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculty academic scoping assignment confirmed.")
            return redirect("academics:teacher_assignments")

    context = {
        "title": "Faculty Academic Scoping Assignments",
        "assignments": assignments,
        "form": form,
    }
    return render(request, "academics/teacher_assignments.html", context)
