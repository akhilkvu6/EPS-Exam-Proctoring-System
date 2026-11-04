import hashlib
import random
from datetime import timedelta
from typing import Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.examinations.models import (
    Examination,
    ExamQuestion,
    CandidateAssignment,
    ExamStatus,
)
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus
from apps.question_bank.services.snapshot import get_student_safe_snapshot_data


@transaction.atomic
def start_or_resume_attempt(
    exam: Examination,
    student: User,
    client_ip: str = None,
    user_agent: str = "",
) -> ExamAttempt:
    """
    Initiates or resumes a candidate examination attempt with strict server-authoritative
    expiry calculation, candidate eligibility checks, and secure snapshot instantiation.
    """
    now = timezone.now()

    # 1. Eligibility Check
    assignment = CandidateAssignment.objects.filter(
        examination=exam,
        student=student,
    ).first()
    if not assignment or not assignment.is_eligible:
        raise ValidationError("You are not authorized or eligible for this examination.")

    # 2. Check Existing Attempt
    attempt = ExamAttempt.objects.filter(
        examination=exam,
        student=student,
    ).first()

    if attempt:
        if attempt.status != AttemptStatus.IN_PROGRESS:
            return attempt
        if attempt.is_expired():
            submit_attempt(attempt, is_auto=True)
            return attempt
        return attempt

    # 3. Exam Schedule Validation for New Attempts
    if exam.status not in [ExamStatus.PUBLISHED, ExamStatus.ACTIVE]:
        raise ValidationError(f"Examination is currently not active (Status: {exam.get_status_display()}).")

    if now < exam.start_window:
        raise ValidationError(f"Examination opens at {exam.start_window.strftime('%Y-%m-%d %H:%M:%S UTC')}.")

    if now > exam.end_window:
        raise ValidationError("The examination deadline has concluded.")

    # Check late join buffer
    if exam.allow_late_join_minutes > 0:
        late_deadline = exam.start_window + timedelta(minutes=exam.allow_late_join_minutes)
        if now > late_deadline:
            raise ValidationError("The late entry grace period for this examination has expired.")

    # 4. Compute Server-Authoritative Expiration
    total_allowed_minutes = exam.duration_minutes + assignment.extra_time_minutes
    computed_expiry = now + timedelta(minutes=total_allowed_minutes)
    authoritative_expiry = min(computed_expiry, exam.end_window)

    # 5. Create Exam Attempt
    attempt = ExamAttempt.objects.create(
        examination=exam,
        student=student,
        expires_at=authoritative_expiry,
        client_ip=client_ip,
        user_agent=user_agent,
        status=AttemptStatus.IN_PROGRESS,
    )

    # 6. Fetch and Instantiate Question Delivery Items
    exam_questions = list(
        ExamQuestion.objects.filter(section__examination=exam)
        .select_related("question", "snapshot")
        .order_by("section__order", "order")
    )

    if not exam_questions:
        raise ValidationError("Examination contains no configured questions.")

    if exam.shuffle_questions:
        # Candidate-specific deterministic pseudo-random shuffle
        rng = random.Random(str(attempt.id))
        rng.shuffle(exam_questions)

    attempt_questions = []
    for idx, eq in enumerate(exam_questions):
        safe_data = get_student_safe_snapshot_data(eq.snapshot)

        # Shuffle options if enabled
        if exam.shuffle_options and "options" in safe_data and isinstance(safe_data["options"], list):
            opt_rng = random.Random(f"{attempt.id}-{eq.id}")
            opt_rng.shuffle(safe_data["options"])

        attempt_questions.append(
            AttemptQuestion(
                attempt=attempt,
                exam_question=eq,
                order=idx + 1,
                safe_payload=safe_data,
            )
        )

    AttemptQuestion.objects.bulk_create(attempt_questions)

    # If exam status is PUBLISHED, set to ACTIVE
    if exam.status == ExamStatus.PUBLISHED:
        exam.status = ExamStatus.ACTIVE
        exam.save(update_fields=["status"])

    return attempt


@transaction.atomic
def submit_attempt(attempt: ExamAttempt, is_auto: bool = False) -> str:
    """
    Finalizes an examination attempt, computes a cryptographic SHA-256 verification
    hash, and transitions the status to SUBMITTED or AUTO_SUBMITTED.
    """
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return attempt.submission_hash

    now = timezone.now()
    answered_count = attempt.attempt_questions.filter(is_answered=True).count()
    hash_payload = (
        f"{attempt.id}:{attempt.student_id}:{now.isoformat()}:{answered_count}:{attempt.examination_id}"
    )
    receipt_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    attempt.status = AttemptStatus.AUTO_SUBMITTED if is_auto else AttemptStatus.SUBMITTED
    attempt.submitted_at = now
    attempt.submission_hash = receipt_hash
    attempt.save(update_fields=["status", "submitted_at", "submission_hash", "updated_at"])

    return receipt_hash
