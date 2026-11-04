"""
Admissions and Official Roll Number Allocation Views for EPS Phoenix.
Compliant with Section 8.5 (Roll allocation ledger and audit history).
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import models
from apps.accounts.decorators import teacher_required
from apps.student.models import StudentProfile
from .models import RollAllocationRecord


@teacher_required
def roll_registry_view(request):
    """
    Central Ledger of Allocated Official Roll Numbers.
    Displays immutable sequential roll records, allocating authority, and verification tickets.
    """
    records_qs = RollAllocationRecord.objects.select_related(
        "student_profile__user",
        "allocated_by",
    ).order_by("-created_at")

    search_query = request.GET.get("q", "").strip()
    if search_query:
        records_qs = records_qs.filter(
            models.Q(allocated_roll_number__icontains=search_query)
            | models.Q(student_profile__registration_number__icontains=search_query)
            | models.Q(student_profile__user__username__icontains=search_query)
            | models.Q(student_profile__user__first_name__icontains=search_query)
            | models.Q(student_profile__user__last_name__icontains=search_query)
        )

    context = {
        "title": "Official Roll Allocation Ledger",
        "records": records_qs[:100],
        "search_query": search_query,
    }
    return render(request, "admissions/roll_registry.html", context)


def application_status_api(request, registration_number):
    """
    Read-only JSON endpoint returning candidate status and verification data.
    """
    profile = get_object_or_404(StudentProfile, registration_number=registration_number)

    return JsonResponse({
        "registration_number": profile.registration_number,
        "candidate_name": profile.user.get_full_name() or profile.user.username,
        "department": profile.department_name,
        "course": profile.course_name,
        "status": profile.admission_status,
        "status_display": profile.get_admission_status_display(),
        "is_approved": profile.is_admission_approved,
        "official_roll_number": profile.roll_number,
    })
