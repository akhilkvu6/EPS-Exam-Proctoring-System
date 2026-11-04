from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import active_user_required
from apps.examinations.models import Examination
from apps.examinations.services.scheduling import check_teacher_exam_access
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.incidents.models import (
    InvigilatorIntervention,
    InterventionAction,
    IncidentReviewRecord,
    FinalDisposition,
)
from apps.incidents.services.intervention import (
    issue_warning,
    grant_time_extension,
    terminate_attempt_for_cause,
    adjudicate_incident,
)


@login_required
@active_user_required
def live_invigilator_console(request, exam_pk):
    """Real-time invigilator dashboard displaying live candidate integrity metrics."""
    user = request.user
    exam = get_object_or_404(
        Examination.objects.select_related("subject", "batch"),
        pk=exam_pk,
    )

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("You do not have invigilation authorization for this examination.")

    attempts = (
        ExamAttempt.objects.filter(examination=exam)
        .select_related("student", "student__student_profile", "proctoring_summary")
        .prefetch_related("interventions")
        .order_by("-started_at")
    )

    filter_suspicious = request.GET.get("suspicious") == "1"
    if filter_suspicious:
        attempts = [a for a in attempts if getattr(a, "proctoring_summary", None) and (
            a.proctoring_summary.requires_human_review or a.proctoring_summary.trust_score < 75
        )]

    context = {
        "exam": exam,
        "attempts": attempts,
        "filter_suspicious": filter_suspicious,
        "total_active": sum(1 for a in attempts if a.status == AttemptStatus.IN_PROGRESS),
        "total_flagged": sum(1 for a in attempts if getattr(a, "proctoring_summary", None) and a.proctoring_summary.requires_human_review),
    }
    return render(request, "incidents/live_console.html", context)


@login_required
@active_user_required
@require_POST
def invigilator_action_view(request, attempt_id):
    """Dispatches a faculty intervention action (warning, time extension, termination)."""
    user = request.user
    attempt = get_object_or_404(ExamAttempt.objects.select_related("examination"), id=attempt_id)

    if not check_teacher_exam_access(user, attempt.examination):
        raise PermissionDenied("Unauthorized action.")

    action = request.POST.get("action")
    notes = request.POST.get("notes", "")

    if action == "warning":
        msg = request.POST.get("message", "Please maintain focus on your screen.")
        issue_warning(attempt, user, msg, notes=notes)
        messages.success(request, f"Official warning issued to {attempt.student.username}.")

    elif action == "extend_time":
        try:
            mins = int(request.POST.get("minutes", 5))
            grant_time_extension(attempt, user, mins, notes=notes)
            messages.success(request, f"Extended timer by {mins} minutes for {attempt.student.username}.")
        except ValueError:
            messages.error(request, "Invalid minutes value.")

    elif action == "terminate":
        terminate_attempt_for_cause(attempt, user, reason=notes or "Proctoring integrity violation")
        messages.error(request, f"Session terminated for {attempt.student.username}.")

    return redirect("incidents:live_console", exam_pk=attempt.examination.pk)


@login_required
@active_user_required
def api_poll_candidate_alerts(request, attempt_id):
    """
    Polled by candidate exam room to receive urgent invigilator notices or time extension updates.
    """
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    unack_interventions = attempt.interventions.filter(is_acknowledged=False).order_by("created_at")
    alerts = []
    for itv in unack_interventions:
        alerts.append({
            "id": str(itv.id),
            "action": itv.action_type,
            "message": itv.message_to_candidate,
            "extra_minutes": itv.granted_extra_minutes,
        })
        itv.is_acknowledged = True
        itv.save(update_fields=["is_acknowledged"])

    is_terminated = attempt.status == AttemptStatus.TERMINATED_SECURITY

    return JsonResponse({
        "alerts": alerts,
        "is_terminated": is_terminated,
        "remaining_seconds": attempt.get_remaining_seconds(),
    })
