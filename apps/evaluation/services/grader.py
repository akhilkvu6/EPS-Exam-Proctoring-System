from decimal import Decimal
from typing import Tuple, List
from django.db import transaction
from django.utils import timezone
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus
from apps.examinations.models import Examination, ExamStatus
from apps.incidents.models import IncidentReviewRecord


def grade_objective_question(att_q: AttemptQuestion) -> Tuple[Decimal, bool]:
    """
    Evaluates an objective AttemptQuestion deterministically against its
    ground-truth version-locked snapshot solutions.
    Returns (awarded_marks, is_evaluated).
    """
    snapshot_data = att_q.exam_question.snapshot.snapshot_data
    q_type = snapshot_data.get("question_type")
    max_marks = Decimal(str(att_q.exam_question.marks))
    negative_marks = Decimal(str(att_q.exam_question.negative_marks or "0.00"))
    ans = att_q.candidate_answer

    # Subjective items require human faculty rubric evaluation
    if q_type in ["SHORT_ANSWER", "DESCRIPTIVE"]:
        return Decimal("0.00"), False

    # Unattempted questions yield 0 without penalty
    if not att_q.is_answered or not ans:
        return Decimal("0.00"), True

    # 1. Single Choice & True/False
    if q_type in ["MCQ_SINGLE", "TRUE_FALSE"]:
        correct_opt_id = next(
            (opt["id"] for opt in snapshot_data.get("options", []) if opt.get("is_correct")),
            None,
        )
        selected_ids = ans.get("selected_option_ids", [])
        if selected_ids and selected_ids[0] == correct_opt_id:
            return max_marks, True
        return -negative_marks, True

    # 2. Multiple Choice
    elif q_type == "MCQ_MULTI":
        correct_ids = {
            opt["id"] for opt in snapshot_data.get("options", []) if opt.get("is_correct")
        }
        selected_ids = set(ans.get("selected_option_ids", []))
        if selected_ids == correct_ids and len(correct_ids) > 0:
            return max_marks, True
        return -negative_marks, True

    # 3. Numerical with Tolerance Window
    elif q_type == "NUMERICAL":
        target = snapshot_data.get("numerical_target")
        tolerance = snapshot_data.get("numerical_tolerance", 0.0)
        cand_val = ans.get("value")
        if target is not None and cand_val is not None:
            if abs(float(cand_val) - float(target)) <= float(tolerance):
                return max_marks, True
        return -negative_marks, True

    # 4. Fill in the Blanks
    elif q_type == "FILL_BLANKS":
        valid_keys = [
            str(opt.get("option_text", "")).strip().lower()
            for opt in snapshot_data.get("options", [])
            if opt.get("is_correct")
        ]
        cand_text = str(ans.get("text", "")).strip().lower()
        if cand_text and cand_text in valid_keys:
            return max_marks, True
        return -negative_marks, True

    return Decimal("0.00"), True


@transaction.atomic
def evaluate_attempt_objective_items(attempt: ExamAttempt) -> int:
    """
    Evaluates all objective assessment questions for an attempt.
    Returns count of graded items.
    """
    graded_count = 0
    for att_q in attempt.attempt_questions.select_related("exam_question__snapshot").all():
        awarded, is_eval = grade_objective_question(att_q)
        if is_eval:
            att_q.awarded_marks = awarded
            att_q.is_evaluated = True
            att_q.save(update_fields=["awarded_marks", "is_evaluated"])
            graded_count += 1

    calculate_and_finalize_attempt_score(attempt)
    return graded_count


@transaction.atomic
def calculate_and_finalize_attempt_score(attempt: ExamAttempt) -> Decimal:
    """
    Sums marks for all evaluated questions, applies any disciplinary penalties,
    clamps to >= 0, and updates attempt status if all questions are completed.
    """
    all_questions = list(attempt.attempt_questions.all())
    total = sum((q.awarded_marks or Decimal("0.00")) for q in all_questions if q.is_evaluated)

    # Disciplinary penalty check
    review = getattr(attempt, "incident_review", None)
    if review and review.penalty_percentage > Decimal("0.00"):
        penalty_amt = (total * review.penalty_percentage) / Decimal("100.00")
        total = total - penalty_amt

    final_score = max(Decimal("0.00"), total)
    attempt.total_score = final_score

    all_done = all(q.is_evaluated for q in all_questions)
    if all_done and attempt.status in [AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED]:
        attempt.status = AttemptStatus.EVALUATED

    attempt.save(update_fields=["total_score", "status", "updated_at"])
    return final_score


@transaction.atomic
def evaluate_entire_exam_cohort(exam: Examination) -> Tuple[int, int]:
    """
    Triggers auto-grading for all submitted attempts in an examination cohort.
    Returns (total_attempts_graded, pending_subjective_items).
    """
    attempts = exam.attempts.filter(
        status__in=[AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.EVALUATED]
    )

    total_graded = 0
    total_pending_subjective = 0

    for attempt in attempts:
        evaluate_attempt_objective_items(attempt)
        pending_subjective = attempt.attempt_questions.filter(is_evaluated=False).count()
        total_pending_subjective += pending_subjective
        total_graded += 1

    if exam.status == ExamStatus.CLOSED or exam.status == ExamStatus.ACTIVE:
        exam.status = ExamStatus.EVALUATION
        exam.save(update_fields=["status"])

    return total_graded, total_pending_subjective
