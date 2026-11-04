import hashlib
from decimal import Decimal
from typing import Tuple
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.examinations.models import Examination, ExamStatus
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.results.models import ExaminationResult, calculate_grade_letter


@transaction.atomic
def publish_examination_results(exam: Examination, published_by: User) -> Tuple[bool, str, int]:
    """
    Finalizes grading, computes grade letters and verification hashes,
    generates published ExaminationResult records, and transitions exam status.
    """
    attempts = exam.attempts.filter(
        status__in=[AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.EVALUATED]
    ).select_related("student", "student__student_profile")

    if not attempts.exists():
        return False, "No completed attempts found to publish.", 0

    published_count = 0
    now = timezone.now()

    for attempt in attempts:
        total_score = attempt.total_score if attempt.total_score is not None else Decimal("0.00")
        max_score = exam.total_marks if exam.total_marks > Decimal("0.00") else Decimal("100.00")

        percentage = round((total_score / max_score) * Decimal("100.00"), 2)
        grade = calculate_grade_letter(percentage)
        is_passed = percentage >= exam.pass_percentage

        # Cryptographic Verification Hash
        roll = (
            attempt.student.student_profile.roll_number
            if hasattr(attempt.student, "student_profile")
            else attempt.student.username
        )
        hash_seed = f"{roll}:{exam.code}:{total_score}:{now.date().isoformat()}:{attempt.id}"
        v_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()

        ExaminationResult.objects.update_or_create(
            attempt=attempt,
            defaults={
                "examination": exam,
                "student": attempt.student,
                "total_score": total_score,
                "maximum_score": max_score,
                "percentage": percentage,
                "grade_letter": grade,
                "is_passed": is_passed,
                "verification_hash": v_hash,
                "is_published": True,
            },
        )
        published_count += 1

    exam.status = ExamStatus.RESULTS_PUBLISHED
    exam.save(update_fields=["status", "updated_at"])

    return True, f"Successfully published results for {published_count} candidates.", published_count
