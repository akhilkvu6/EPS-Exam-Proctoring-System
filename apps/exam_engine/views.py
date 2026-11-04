import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import active_user_required
from apps.examinations.models import Examination, CandidateAssignment
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus
from apps.exam_engine.services.delivery import start_or_resume_attempt, submit_attempt


@login_required
@active_user_required
def exam_lobby_view(request, exam_code):
    """Pre-exam lobby displaying instructions, duration, and launch action."""
    user = request.user
    if user.role != "STUDENT":
        raise PermissionDenied("Only students can enter an examination lobby.")

    exam = get_object_or_404(
        Examination.objects.select_related("subject", "batch"),
        code=exam_code,
    )

    assignment = CandidateAssignment.objects.filter(
        examination=exam,
        student=user,
    ).first()

    if not assignment or not assignment.is_eligible:
        messages.error(request, "You are not enrolled or eligible for this examination.")
        return redirect("student:dashboard")

    # Check if candidate has an existing attempt
    existing_attempt = ExamAttempt.objects.filter(examination=exam, student=user).first()
    if existing_attempt and existing_attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("exam_engine:exam_receipt", attempt_id=existing_attempt.id)

    if request.method == "POST":
        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")
        try:
            attempt = start_or_resume_attempt(exam, user, client_ip=ip, user_agent=ua)
            return redirect("exam_engine:exam_room", attempt_id=attempt.id)
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    context = {
        "exam": exam,
        "assignment": assignment,
        "existing_attempt": existing_attempt,
        "total_minutes": exam.duration_minutes + assignment.extra_time_minutes,
    }
    return render(request, "exam_engine/lobby.html", context)


@login_required
@active_user_required
def exam_room_view(request, attempt_id):
    """Full-screen distraction-free examination delivery room."""
    user = request.user
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("examination", "examination__subject"),
        id=attempt_id,
    )

    # IDOR and role boundary protection
    if attempt.student != user:
        raise PermissionDenied("Unauthorized attempt access.")

    # Check if already completed or expired
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("exam_engine:exam_receipt", attempt_id=attempt.id)

    if attempt.is_expired():
        submit_attempt(attempt, is_auto=True)
        return redirect("exam_engine:exam_receipt", attempt_id=attempt.id)

    remaining_seconds = attempt.get_remaining_seconds()
    questions = attempt.attempt_questions.all().order_by("order")

    context = {
        "attempt": attempt,
        "exam": attempt.examination,
        "remaining_seconds": remaining_seconds,
        "questions": questions,
        "total_questions": questions.count(),
        "calculator_enabled": attempt.examination.calculator_enabled,
        "strict_proctoring": attempt.examination.strict_proctoring,
    }
    return render(request, "exam_engine/room.html", context)


@login_required
@active_user_required
def exam_receipt_view(request, attempt_id):
    """Displays cryptographic submission receipt and verification confirmation."""
    user = request.user
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("examination", "examination__subject"),
        id=attempt_id,
    )

    # Faculty/admin or the candidate can view the receipt
    if user != attempt.student and user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Unauthorized receipt access.")

    answered_count = attempt.attempt_questions.filter(is_answered=True).count()
    total_count = attempt.attempt_questions.count()

    context = {
        "attempt": attempt,
        "exam": attempt.examination,
        "answered_count": answered_count,
        "total_count": total_count,
    }
    return render(request, "exam_engine/receipt.html", context)


# ==========================================
# REST / JSON Server-Authoritative APIs
# ==========================================

@login_required
@active_user_required
def api_get_timer(request, attempt_id):
    """Returns server-authoritative timer value and expiration status."""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    if attempt.status != AttemptStatus.IN_PROGRESS or attempt.is_expired():
        if attempt.status == AttemptStatus.IN_PROGRESS:
            submit_attempt(attempt, is_auto=True)
        return JsonResponse({"remaining_seconds": 0, "is_expired": True, "status": attempt.status})

    return JsonResponse({
        "remaining_seconds": attempt.get_remaining_seconds(),
        "is_expired": False,
        "status": attempt.status,
    })


@login_required
@active_user_required
@require_POST
def api_save_answer(request, attempt_id, question_id):
    """
    Saves an answer for an AttemptQuestion.
    Rejects saves if the server-authoritative timer has expired.
    """
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    if attempt.status != AttemptStatus.IN_PROGRESS or attempt.is_expired():
        if attempt.status == AttemptStatus.IN_PROGRESS:
            submit_attempt(attempt, is_auto=True)
        return JsonResponse({"error": "Examination timer has expired."}, status=403)

    att_q = get_object_or_404(AttemptQuestion, id=question_id, attempt=attempt)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body.")

    answer_payload = body.get("answer", {})
    time_spent = body.get("time_spent_seconds", 0)

    # Determine if considered answered
    is_answered = bool(answer_payload)
    if isinstance(answer_payload, dict):
        if "selected_option_ids" in answer_payload:
            is_answered = len(answer_payload["selected_option_ids"]) > 0
        elif "text" in answer_payload:
            is_answered = len(str(answer_payload["text"]).strip()) > 0
        elif "value" in answer_payload:
            is_answered = answer_payload["value"] is not None

    att_q.candidate_answer = answer_payload
    att_q.is_answered = is_answered
    if time_spent > 0:
        att_q.time_spent_seconds += int(time_spent)
    att_q.save(update_fields=["candidate_answer", "is_answered", "time_spent_seconds"])

    return JsonResponse({"status": "saved", "is_answered": att_q.is_answered})


@login_required
@active_user_required
@require_POST
def api_toggle_flag(request, attempt_id, question_id):
    """Toggles review flag for an AttemptQuestion."""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return JsonResponse({"error": "Examination is not active."}, status=403)

    att_q = get_object_or_404(AttemptQuestion, id=question_id, attempt=attempt)
    att_q.is_flagged_for_review = not att_q.is_flagged_for_review
    att_q.save(update_fields=["is_flagged_for_review"])

    return JsonResponse({"is_flagged": att_q.is_flagged_for_review})


@login_required
@active_user_required
@require_POST
def api_submit_exam(request, attempt_id):
    """Candidate manual exam submission trigger."""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return JsonResponse({"status": "already_submitted", "receipt": attempt.submission_hash})

    receipt_hash = submit_attempt(attempt, is_auto=False)
    return JsonResponse({
        "status": "submitted",
        "receipt": receipt_hash,
        "redirect_url": f"/exam/receipt/{attempt.id}/",
    })
