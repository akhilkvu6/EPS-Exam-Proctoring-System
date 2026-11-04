"""
Student Workspace Views for EPS Phoenix.
Compliant with Section 7 (Student permissions) and Section 21 (Student Workspace).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from apps.accounts.decorators import student_required, active_user_required
from apps.accounts.models import UserRole, UserStatus
from .models import StudentProfile, AdmissionApplicationStatus
from .forms import StudentRegistrationForm, StudentProfileEditForm
import logging

logger = logging.getLogger(__name__)


def get_or_create_student_profile(user) -> StudentProfile:
    """Helper ensuring a StudentProfile exists for the student user."""
    profile, created = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            "registration_number": f"REG-{user.id:05d}",
            "department_name": "General Department",
            "course_name": "Undergraduate Studies",
            "batch_name": "2024-2028",
            "admission_status": AdmissionApplicationStatus.APPROVED if user.status == UserStatus.ACTIVE else AdmissionApplicationStatus.SUBMITTED,
        },
    )
    return profile


def student_register(request):
    """
    Public student self-registration endpoint for admission applications.
    """
    if request.user.is_authenticated:
        return redirect("student:dashboard")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            profile = form.save()
            # Log in candidate automatically to access admission tracking
            login(request, profile.user)
            messages.success(
                request,
                f"Application submitted successfully! Your application reference number is {profile.registration_number}.",
            )
            return redirect("student:admission_status")
    else:
        form = StudentRegistrationForm()

    context = {
        "form": form,
        "title": "Student Admission Registration",
    }
    return render(request, "student/register.html", context)


@login_required
def admission_status_view(request):
    """
    Candidate admission status & approval tracking timeline.
    Accessible to pending applicants who do not yet have active workspace privileges.
    """
    if request.user.role != UserRole.STUDENT and not request.user.is_superuser:
        raise PermissionDenied("Only student candidates may access application status.")

    profile = get_or_create_student_profile(request.user)

    context = {
        "profile": profile,
        "title": "Admission Application Status",
    }
    return render(request, "student/admission_status.html", context)


@student_required
def dashboard_view(request):
    """
    Primary Student Workspace Dashboard.
    Provides candidate identification, enrolled courses, active exams, and results.
    """
    profile = get_or_create_student_profile(request.user)

    context = {
        "profile": profile,
        "title": "Student Workspace",
        "active_exams_count": 0,
        "completed_exams_count": 0,
        "published_results_count": 0,
    }
    return render(request, "student/dashboard.html", context)


@student_required
def profile_view(request):
    """
    Student profile overview and permitted personal details update.
    Protects official roll number and academic assignments from tampering.
    """
    profile = get_or_create_student_profile(request.user)

    if request.method == "POST":
        form = StudentProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile details updated successfully.")
            return redirect("student:profile")
    else:
        form = StudentProfileEditForm(instance=profile)

    context = {
        "profile": profile,
        "form": form,
        "title": "Student Profile & Identity",
    }
    return render(request, "student/profile.html", context)


@student_required
def academics_view(request):
    """
    Academic enrollment, course specifications, and semester curriculum view.
    """
    profile = get_or_create_student_profile(request.user)

    context = {
        "profile": profile,
        "title": "Enrolled Academic Curriculum",
    }
    return render(request, "student/academics.html", context)


@student_required
def exams_list_view(request):
    """
    Candidate examination portal overview (active, scheduled, and past attempts).
    """
    profile = get_or_create_student_profile(request.user)

    context = {
        "profile": profile,
        "title": "Examinations Portal",
        "exams": [],  # Scheduled for Phase 10 delivery engine
    }
    return render(request, "student/exams_list.html", context)


@student_required
def results_list_view(request):
    """
    Candidate published scorecards and PDF verification portal.
    """
    profile = get_or_create_student_profile(request.user)

    context = {
        "profile": profile,
        "title": "Results & Scorecards",
        "results": [],  # Scheduled for Phase 16 PDF results engine
    }
    return render(request, "student/results_list.html", context)
