import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.accounts.decorators import active_user_required
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.proctoring.services.noise_filter import record_proctoring_event


@login_required
@active_user_required
@require_POST
def api_log_event(request, attempt_id):
    """
    Ingests fine-grained browser and vision integrity telemetry from active exam rooms.
    Applies noise filtering and updates the candidate's real-time trust score.
    """
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    if attempt.status != AttemptStatus.IN_PROGRESS:
        return JsonResponse({"error": "Attempt is not active."}, status=403)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body.")

    event_type = body.get("event_type")
    if not event_type:
        return HttpResponseBadRequest("Missing event_type parameter.")

    duration_seconds = float(body.get("duration_seconds", 0.0))
    metadata = body.get("metadata", {})

    event, summary = record_proctoring_event(
        attempt=attempt,
        event_type=event_type,
        duration_seconds=duration_seconds,
        metadata=metadata,
    )

    return JsonResponse({
        "status": "recorded",
        "event_id": str(event.id),
        "is_noise_filtered": event.is_noise_filtered,
        "trust_score": float(summary.trust_score),
        "requires_review": summary.requires_human_review,
    })


@login_required
@active_user_required
def api_get_proctoring_status(request, attempt_id):
    """Fetches candidate trust score and aggregated telemetry."""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id)

    # Scoped to candidate or teachers/admins
    if request.user != attempt.student and request.user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Access denied.")

    summary = getattr(attempt, "proctoring_summary", None)
    if not summary:
        return JsonResponse({"trust_score": 100.0, "requires_review": False})

    return JsonResponse({
        "trust_score": float(summary.trust_score),
        "requires_review": summary.requires_human_review,
        "fullscreen_exits": summary.fullscreen_exit_count,
        "tab_switches": summary.tab_switch_count,
        "total_out_of_focus_seconds": summary.total_out_of_focus_seconds,
    })
