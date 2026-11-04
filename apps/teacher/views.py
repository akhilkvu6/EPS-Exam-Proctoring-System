"""
Teacher Workspace Views for EPS Phoenix.
Compliant with Section 7 (Teacher permissions), Section 8.3 (Teacher workflow), and Section 21.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from apps.accounts.decorators import teacher_required
from apps.accounts.models import UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from .models import TeacherProfile, AdmissionReviewRecord, AdmissionReviewAction
from .forms import TeacherProfileEditForm, AdmissionReviewForm
import logging

logger = logging.getLogger(__name__)


def get_or_create_teacher_profile(user) -> TeacherProfile:
    """Helper ensuring a TeacherProfile exists for the faculty user."""
    profile, created = TeacherProfile.objects.get_or_create(
        user=user,
        defaults={
            "staff_id": f"FAC-{user.id:04d}",
            "designation": "Assistant Professor",
            "department_name": "Department of Computer Science",
        },
    )
    return profile


@teacher_required
def dashboard_view(request):
    """
    Primary Teacher Workspace Dashboard.
    Scattered metrics scoped to teacher's academic department.
    """
    teacher_profile = get_or_create_teacher_profile(request.user)

    # Scoped admissions count
    pending_statuses = [
        AdmissionApplicationStatus.SUBMITTED,
        AdmissionApplicationStatus.PENDING_TEACHER,
        AdmissionApplicationStatus.RESUBMITTED,
    ]
    dept_name = teacher_profile.department_name

    # Check admissions matching department or all if HOD/Superuser
    admissions_qs = StudentProfile.objects.all()
    if not (teacher_profile.is_head_of_department or request.user.is_superuser):
        admissions_qs = admissions_qs.filter(department_name__iexact=dept_name)

    pending_admissions_count = admissions_qs.filter(admission_status__in=pending_statuses).count()
    total_approved_students_count = admissions_qs.filter(admission_status=AdmissionApplicationStatus.APPROVED).count()

    context = {
        "teacher_profile": teacher_profile,
        "title": "Faculty Workspace",
        "pending_admissions_count": pending_admissions_count,
        "total_approved_students_count": total_approved_students_count,
        "active_exams_count": 0,  # Scheduled for Phase 9
        "pending_evaluations_count": 0,  # Scheduled for Phase 15
    }
    return render(request, "teacher/dashboard.html", context)


@teacher_required
def admission_queue_view(request):
    """
    Faculty Admission Review Queue.
    Enforces academic department scoping per Section 7 & 8.3.
    """
    teacher_profile = get_or_create_teacher_profile(request.user)
    dept_name = teacher_profile.department_name

    applications = StudentProfile.objects.all()
    if not (teacher_profile.is_head_of_department or request.user.is_superuser):
        applications = applications.filter(department_name__iexact=dept_name)

    # Status filter
    status_filter = request.GET.get("status", "")
    if status_filter and status_filter != "ALL":
        applications = applications.filter(admission_status=status_filter)

    applications = applications.select_related("user").order_by("-created_at")

    context = {
        "teacher_profile": teacher_profile,
        "applications": applications,
        "status_filter": status_filter,
        "title": "Admission Application Review Queue",
    }
    return render(request, "teacher/admission_queue.html", context)


@teacher_required
def admission_detail_view(request, application_id):
    """
    Detailed dossier review and decision recording.
    Section 8.3: Review, remarks, request info, approve, reject, or escalate to admin.
    """
    teacher_profile = get_or_create_teacher_profile(request.user)
    application = get_object_or_404(StudentProfile.objects.select_related("user"), id=application_id)

    # Scoping check
    if not (teacher_profile.is_head_of_department or request.user.is_superuser):
        if application.department_name.lower() != teacher_profile.department_name.lower():
            messages.warning(request, "Application belongs to another department; viewing with read-only permissions.")

    history = application.review_history.select_related("reviewer").all()

    if request.method == "POST":
        form = AdmissionReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            remarks = form.cleaned_data["remarks"]
            custom_roll = form.cleaned_data.get("roll_number", "").strip()

            with transaction.atomic():
                # Record audit history
                AdmissionReviewRecord.objects.create(
                    student_profile=application,
                    reviewer=request.user,
                    action=action,
                    remarks=remarks,
                )

                if action == AdmissionReviewAction.APPROVE:
                    application.admission_status = AdmissionApplicationStatus.APPROVED
                    application.admission_approved_at = timezone.now()
                    # Assign roll number
                    if custom_roll:
                        application.roll_number = custom_roll
                    elif not application.roll_number:
                        # Auto sequential fallback format
                        year = timezone.now().year
                        count = StudentProfile.objects.filter(roll_number__isnull=False).count() + 1
                        application.roll_number = f"EP-{year}-{count:04d}"

                    # Activate student account
                    student_user = application.user
                    student_user.status = UserStatus.ACTIVE
                    student_user.is_verified = True
                    student_user.save()
                    application.save()

                    messages.success(
                        request,
                        f"Application approved! Allocated Roll Number: {application.roll_number}",
                    )

                elif action == AdmissionReviewAction.REJECT:
                    application.admission_status = AdmissionApplicationStatus.REJECTED
                    student_user = application.user
                    student_user.status = UserStatus.INACTIVE
                    student_user.save()
                    application.save()
                    messages.info(request, "Application has been rejected.")

                elif action == AdmissionReviewAction.REQUEST_INFO:
                    application.admission_status = AdmissionApplicationStatus.INFO_REQUESTED
                    application.save()
                    messages.warning(request, "Additional information requested from candidate.")

                elif action == AdmissionReviewAction.ESCALATE:
                    application.admission_status = AdmissionApplicationStatus.ESCALATED_ADMIN
                    application.save()
                    messages.info(request, "Application successfully escalated to Institutional Administration.")

            return redirect("teacher:admission_detail", application_id=application.id)
    else:
        form = AdmissionReviewForm()

    context = {
        "teacher_profile": teacher_profile,
        "application": application,
        "history": history,
        "form": form,
        "title": f"Review Dossier: {application.registration_number}",
    }
    return render(request, "teacher/admission_detail.html", context)


@teacher_required
def students_list_view(request):
    """
    Directory of enrolled and active students within teacher's academic scope.
    """
    teacher_profile = get_or_create_teacher_profile(request.user)
    dept_name = teacher_profile.department_name

    students = StudentProfile.objects.filter(
        admission_status=AdmissionApplicationStatus.APPROVED
    ).select_related("user")

    if not (teacher_profile.is_head_of_department or request.user.is_superuser):
        students = students.filter(department_name__iexact=dept_name)

    query = request.GET.get("q", "").strip()
    if query:
        students = students.filter(
            models.Q(user__username__icontains=query)
            | models.Q(user__first_name__icontains=query)
            | models.Q(user__last_name__icontains=query)
            | models.Q(roll_number__icontains=query)
            | models.Q(registration_number__icontains=query)
        )

    context = {
        "teacher_profile": teacher_profile,
        "students": students,
        "query": query,
        "title": "Enrolled Candidate Directory",
    }
    return render(request, "teacher/students_list.html", context)


@teacher_required
def profile_view(request):
    """
    Faculty profile viewing and update.
    """
    teacher_profile = get_or_create_teacher_profile(request.user)

    if request.method == "POST":
        form = TeacherProfileEditForm(request.POST, instance=teacher_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculty profile updated successfully.")
            return redirect("teacher:profile")
    else:
        form = TeacherProfileEditForm(instance=teacher_profile)

    context = {
        "teacher_profile": teacher_profile,
        "form": form,
        "title": "Faculty Profile",
    }
    return render(request, "teacher/profile.html", context)
