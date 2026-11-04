from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import active_user_required
from apps.examinations.models import Examination, ExamStatus
from apps.examinations.services.scheduling import check_teacher_exam_access
from apps.academics.services.scoping import (
    get_teacher_assigned_subjects,
    get_teacher_assigned_batches,
)
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus
from apps.evaluation.services.grader import (
    evaluate_attempt_objective_items,
    evaluate_entire_exam_cohort,
    calculate_and_finalize_attempt_score,
)


@login_required
@active_user_required
def evaluation_queue_view(request):
    """Faculty assessment evaluation queue listing exams with submissions awaiting grading."""
    user = request.user
    if user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Only faculty and administrators can access evaluation queues.")

    if user.role == "TEACHER":
        subjects = get_teacher_assigned_subjects(user)
        batches = get_teacher_assigned_batches(user)
        exams = Examination.objects.filter(subject__in=subjects, batch__in=batches)
    else:
        exams = Examination.objects.all()

    exams_data = []
    for exam in exams.select_related("subject", "batch"):
        attempts = exam.attempts.filter(
            status__in=[AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.EVALUATED]
        )
        total_sub = attempts.count()
        if total_sub > 0:
            pending_subjective = AttemptQuestion.objects.filter(
                attempt__in=attempts,
                is_evaluated=False,
            ).count()
            exams_data.append({
                "exam": exam,
                "total_submissions": total_sub,
                "pending_subjective": pending_subjective,
            })

    return render(request, "evaluation/queue.html", {"exams_data": exams_data})


@login_required
@active_user_required
def exam_evaluation_overview_view(request, exam_pk):
    """Cohort evaluation overview with batch auto-grader action and candidate dossier table."""
    user = request.user
    exam = get_object_or_404(
        Examination.objects.select_related("subject", "batch"),
        pk=exam_pk,
    )

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Unauthorized evaluation access.")

    if request.method == "POST" and "run_autograder" in request.POST:
        graded_cnt, pending_cnt = evaluate_entire_exam_cohort(exam)
        messages.success(
            request,
            f"Auto-grader executed across {graded_cnt} candidate submissions. {pending_cnt} subjective items require faculty grading.",
        )
        return redirect("evaluation:exam_overview", exam_pk=exam.pk)

    attempts = (
        exam.attempts.filter(
            status__in=[AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.EVALUATED]
        )
        .select_related("student", "student__student_profile")
        .prefetch_related("attempt_questions")
        .order_by("student__username")
    )

    pending_items = (
        AttemptQuestion.objects.filter(
            attempt__examination=exam,
            is_evaluated=False,
        )
        .select_related("attempt__student", "exam_question__question")
        .order_by("order")
    )

    context = {
        "exam": exam,
        "attempts": attempts,
        "pending_items": pending_items,
        "total_pending_subjective": pending_items.count(),
    }
    return render(request, "evaluation/exam_overview.html", context)


@login_required
@active_user_required
@transaction.atomic
def grade_subjective_item_view(request, attempt_q_id):
    """Rubric-guided grading form for individual subjective/descriptive questions."""
    user = request.user
    att_q = get_object_or_404(
        AttemptQuestion.objects.select_related(
            "attempt__examination",
            "attempt__student",
            "attempt__student__student_profile",
            "exam_question__question",
            "exam_question__snapshot",
        ),
        id=attempt_q_id,
    )

    exam = att_q.attempt.examination
    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Unauthorized grading access.")

    snapshot_data = att_q.exam_question.snapshot.snapshot_data
    max_marks = Decimal(str(att_q.exam_question.marks))

    if request.method == "POST":
        try:
            score_input = request.POST.get("awarded_marks", "0.0")
            awarded = Decimal(score_input)
            feedback = request.POST.get("evaluator_feedback", "").strip()

            if awarded < Decimal("0.00") or awarded > max_marks:
                messages.error(request, f"Awarded marks must be between 0.00 and {max_marks}.")
            else:
                att_q.awarded_marks = awarded
                att_q.evaluator_feedback = feedback
                att_q.is_evaluated = True
                att_q.save(update_fields=["awarded_marks", "evaluator_feedback", "is_evaluated"])

                # Recompute attempt total score
                calculate_and_finalize_attempt_score(att_q.attempt)
                messages.success(request, f"Evaluated response for {att_q.attempt.student.username} (+{awarded} pts).")
                return redirect("evaluation:exam_overview", exam_pk=exam.pk)
        except Exception as e:
            messages.error(request, f"Grading error: {str(e)}")

    context = {
        "att_q": att_q,
        "exam": exam,
        "snapshot_data": snapshot_data,
        "max_marks": max_marks,
    }
    return render(request, "evaluation/grade_item.html", context)
