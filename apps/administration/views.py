"""
Institutional Administration Views for EPS Phoenix.
Compliant with Section 7 (Admin permissions), Section 8.4 (Admin workflow), and Section 21.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction, models
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from apps.accounts.decorators import admin_required
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.teacher.models import TeacherProfile, AdmissionReviewRecord, AdmissionReviewAction
from .models import InstitutionSetting, SystemAuditLog
from .forms import InstitutionSettingsForm, TeacherCreateForm, AdminEscalationDecisionForm
import logging

logger = logging.getLogger(__name__)


def log_audit_action(actor, action_type: str, target_repr: str, details: str, request=None):
    """Utility function creating immutable administrative audit entries."""
    ip_addr = None
    if request:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_addr = x_forwarded_for.split(",")[0].strip()
        else:
            ip_addr = request.META.get("REMOTE_ADDR")

    SystemAuditLog.objects.create(
        actor=actor,
        action_type=action_type,
        target_repr=target_repr,
        ip_address=ip_addr,
        details=details,
    )
    logger.info(f"[AUDIT] {action_type} by {actor.username if actor else 'System'}: {target_repr} - {details}")


@admin_required
def dashboard_view(request):
    """
    Central Institutional Administration Dashboard.
    Provides institutional metrics, pending escalations, and system health status.
    """
    total_students = User.objects.filter(role=UserRole.STUDENT).count()
    total_teachers = User.objects.filter(role=UserRole.TEACHER).count()
    pending_escalations = StudentProfile.objects.filter(
        admission_status=AdmissionApplicationStatus.ESCALATED_ADMIN
    ).count()
    suspended_accounts = User.objects.filter(status=UserStatus.SUSPENDED).count()

    recent_audits = SystemAuditLog.objects.select_related("actor")[:8]
    settings_obj = InstitutionSetting.get_settings()

    context = {
        "title": "Institutional Administration",
        "total_students": total_students,
        "total_teachers": total_teachers,
        "pending_escalations": pending_escalations,
        "suspended_accounts": suspended_accounts,
        "recent_audits": recent_audits,
        "settings_obj": settings_obj,
    }
    return render(request, "administration/dashboard.html", context)


@admin_required
def escalated_admissions_view(request):
    """
    Section 8.4: View admission applications escalated to Admin from faculty review.
    """
    escalations = StudentProfile.objects.filter(
        admission_status=AdmissionApplicationStatus.ESCALATED_ADMIN
    ).select_related("user").order_by("-updated_at")

    context = {
        "title": "Escalated Admission Applications",
        "escalations": escalations,
    }
    return render(request, "administration/escalations.html", context)


@admin_required
def escalation_detail_view(request, application_id):
    """
    Section 8.4: Review faculty remarks, examine candidate dossier, and record
    authoritative administrative determination (Approve, Reject, or Return to Teacher).
    """
    application = get_object_or_404(
        StudentProfile.objects.select_related("user"),
        id=application_id,
    )
    history = application.review_history.select_related("reviewer").all()
    settings_obj = InstitutionSetting.get_settings()

    if request.method == "POST":
        form = AdminEscalationDecisionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            remarks = form.cleaned_data["remarks"]
            custom_roll = form.cleaned_data.get("roll_number", "").strip()

            with transaction.atomic():
                if action == "APPROVE":
                    application.admission_status = AdmissionApplicationStatus.APPROVED
                    application.admission_approved_at = timezone.now()
                    if custom_roll:
                        application.roll_number = custom_roll
                    elif not application.roll_number:
                        year = timezone.now().year
                        prefix = settings_obj.roll_number_prefix or "EP"
                        count = StudentProfile.objects.filter(roll_number__isnull=False).count() + 1
                        application.roll_number = f"{prefix}-{year}-{count:04d}"

                    student_user = application.user
                    student_user.status = UserStatus.ACTIVE
                    student_user.is_verified = True
                    student_user.save()
                    application.save()

                    # Record faculty history and central audit log
                    AdmissionReviewRecord.objects.create(
                        student_profile=application,
                        reviewer=request.user,
                        action=AdmissionReviewAction.APPROVE,
                        remarks=f"[ADMIN RESOLUTION] {remarks}",
                    )
                    log_audit_action(
                        request.user,
                        "ESCALATION_APPROVED",
                        f"{application.registration_number} ({student_user.username})",
                        f"Approved by Admin with roll number {application.roll_number}. Remarks: {remarks}",
                        request,
                    )
                    messages.success(
                        request,
                        f"Application approved by Administration! Allocated Roll: {application.roll_number}",
                    )

                elif action == "REJECT":
                    application.admission_status = AdmissionApplicationStatus.REJECTED
                    student_user = application.user
                    student_user.status = UserStatus.INACTIVE
                    student_user.save()
                    application.save()

                    AdmissionReviewRecord.objects.create(
                        student_profile=application,
                        reviewer=request.user,
                        action=AdmissionReviewAction.REJECT,
                        remarks=f"[ADMIN REJECTION] {remarks}",
                    )
                    log_audit_action(
                        request.user,
                        "ESCALATION_REJECTED",
                        f"{application.registration_number} ({student_user.username})",
                        f"Application rejected by Admin. Remarks: {remarks}",
                        request,
                    )
                    messages.info(request, "Application rejected by Administration.")

                elif action == "RETURN":
                    application.admission_status = AdmissionApplicationStatus.PENDING_TEACHER
                    application.save()

                    AdmissionReviewRecord.objects.create(
                        student_profile=application,
                        reviewer=request.user,
                        action=AdmissionReviewAction.REQUEST_INFO,
                        remarks=f"[ADMIN RETURNED TO FACULTY] {remarks}",
                    )
                    log_audit_action(
                        request.user,
                        "ESCALATION_RETURNED",
                        f"{application.registration_number}",
                        f"Returned to department review queue. Instructions: {remarks}",
                        request,
                    )
                    messages.warning(
                        request,
                        "Application returned to departmental faculty queue with administrative instructions.",
                    )

            return redirect("administration:escalated_admissions")
    else:
        form = AdminEscalationDecisionForm()

    context = {
        "title": f"Resolve Escalation: {application.registration_number}",
        "application": application,
        "history": history,
        "form": form,
    }
    return render(request, "administration/escalation_detail.html", context)


@admin_required
def users_directory_view(request):
    """
    Central user registry across all institutional roles.
    Enables status review, activation, and suspension.
    """
    users_qs = User.objects.all().order_by("-date_joined")

    role_filter = request.GET.get("role", "")
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("q", "").strip()

    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if status_filter:
        users_qs = users_qs.filter(status=status_filter)
    if search_query:
        users_qs = users_qs.filter(
            models.Q(username__icontains=search_query)
            | models.Q(first_name__icontains=search_query)
            | models.Q(last_name__icontains=search_query)
            | models.Q(email__icontains=search_query)
            | models.Q(official_id__icontains=search_query)
        )

    context = {
        "title": "Institutional User Directory",
        "users": users_qs[:100],
        "role_filter": role_filter,
        "status_filter": status_filter,
        "search_query": search_query,
        "roles": UserRole.choices,
        "statuses": UserStatus.choices,
    }
    return render(request, "administration/users_list.html", context)


@admin_required
@require_POST
def user_status_toggle_view(request, user_id):
    """
    Toggles user status between ACTIVE and SUSPENDED with audit verification.
    Prevents self-suspension by administrator.
    """
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot suspend your own administrative account.")
        return redirect("administration:users_directory")

    new_status = request.POST.get("new_status")
    reason = request.POST.get("reason", "Administrative action")

    if new_status in [UserStatus.ACTIVE, UserStatus.SUSPENDED, UserStatus.INACTIVE]:
        prev_status = target_user.status
        target_user.status = new_status
        target_user.save()

        log_audit_action(
            request.user,
            "USER_STATUS_CHANGE",
            f"{target_user.username} ({target_user.get_role_display()})",
            f"Changed status from {prev_status} to {new_status}. Reason: {reason}",
            request,
        )
        messages.success(
            request,
            f"User @{target_user.username} status successfully updated to {new_status}.",
        )
    else:
        messages.error(request, "Invalid status target specified.")

    return redirect("administration:users_directory")


@admin_required
def teachers_management_view(request):
    """
    Faculty roster management and account provisioning.
    """
    teachers = TeacherProfile.objects.select_related("user").all().order_by("department_name")

    if request.method == "POST":
        form = TeacherCreateForm(request.POST)
        if form.is_valid():
            teacher_profile = form.save()
            log_audit_action(
                request.user,
                "TEACHER_PROVISIONED",
                f"{teacher_profile.staff_id} ({teacher_profile.user.username})",
                f"Faculty account provisioned for {teacher_profile.department_name}.",
                request,
            )
            messages.success(
                request,
                f"Faculty account for {teacher_profile.user.get_full_name()} ({teacher_profile.staff_id}) created successfully.",
            )
            return redirect("administration:teachers_management")
    else:
        form = TeacherCreateForm()

    context = {
        "title": "Faculty Management & Provisioning",
        "teachers": teachers,
        "form": form,
    }
    return render(request, "administration/teachers_list.html", context)


@admin_required
def settings_view(request):
    """
    Central institution configuration, appearance defaults, and registration policies.
    """
    settings_obj = InstitutionSetting.get_settings()

    if request.method == "POST":
        form = InstitutionSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()

            log_audit_action(
                request.user,
                "INSTITUTION_SETTINGS_UPDATED",
                updated.institution_name,
                "Branding, theme preferences, and registration policies updated.",
                request,
            )
            messages.success(request, "Institutional settings saved successfully.")
            return redirect("administration:settings")
    else:
        form = InstitutionSettingsForm(instance=settings_obj)

    context = {
        "title": "Institutional Settings & Governance",
        "settings_obj": settings_obj,
        "form": form,
    }
    return render(request, "administration/settings.html", context)


@admin_required
def audit_logs_view(request):
    """
    Chronological security audit trail inspection.
    """
    logs_qs = SystemAuditLog.objects.select_related("actor").order_by("-created_at")

    action_type = request.GET.get("action_type", "")
    if action_type:
        logs_qs = logs_qs.filter(action_type__icontains=action_type)

    context = {
        "title": "Security & Administrative Audit Logs",
        "audit_logs": logs_qs[:200],
        "action_type": action_type,
    }
    return render(request, "administration/audit_logs.html", context)
