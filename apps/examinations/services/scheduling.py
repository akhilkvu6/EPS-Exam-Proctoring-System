from decimal import Decimal
from typing import Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.accounts.models import User, UserRole
from apps.academics.models import TeacherAssignment, StudentEnrollment
from apps.examinations.models import Examination, ExamSection, ExamQuestion, CandidateAssignment, ExamStatus
from apps.question_bank.models import Question
from apps.question_bank.services.snapshot import create_or_get_question_snapshot


def check_teacher_exam_access(user: User, exam: Examination) -> bool:
    """Verifies that the teacher is officially assigned to the exam's subject and batch."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.TEACHER:
        return TeacherAssignment.objects.filter(
            teacher=user,
            subject=exam.subject,
            batch=exam.batch,
            is_active=True,
        ).exists()
    return False


@transaction.atomic
def add_question_to_section(
    section: ExamSection,
    question: Question,
    marks: Decimal = None,
    negative_marks: Decimal = None,
    order: int = None,
) -> ExamQuestion:
    """
    Attaches a question to an exam section and permanently locks in its QuestionSnapshot.
    """
    snapshot = create_or_get_question_snapshot(question)

    if marks is None:
        marks = question.default_marks
    if negative_marks is None:
        negative_marks = question.negative_marks
    if order is None:
        highest_order = (
            ExamQuestion.objects.filter(section=section).order_by("-order").values_list("order", flat=True).first()
        )
        order = (highest_order or 0) + 1

    exam_q = ExamQuestion.objects.create(
        section=section,
        question=question,
        snapshot=snapshot,
        order=order,
        marks=marks,
        negative_marks=negative_marks,
    )

    section.examination.recalculate_total_marks()
    return exam_q


@transaction.atomic
def publish_examination(exam: Examination, triggered_by: User) -> Tuple[bool, str, int]:
    """
    Validates configuration, snapshots questions, auto-provisions candidate roster
    from academic cohort enrollments, and transitions status to PUBLISHED.
    """
    if exam.status in [ExamStatus.PUBLISHED, ExamStatus.ACTIVE, ExamStatus.CLOSED]:
        return False, f"Examination is already in state: {exam.get_status_display()}", 0

    # Ensure sections and questions exist
    sections = exam.sections.all()
    if not sections.exists():
        raise ValidationError("Cannot publish an examination without at least one section.")

    total_questions = ExamQuestion.objects.filter(section__examination=exam).count()
    if total_questions == 0:
        raise ValidationError("Cannot publish an examination without any configured questions.")

    if exam.end_window <= exam.start_window:
        raise ValidationError("End window time must be strictly after start window time.")

    # Recalculate marks
    exam.recalculate_total_marks()

    # Provision candidate assignments from enrolled students
    enrollments = StudentEnrollment.objects.filter(
        batch=exam.batch,
        status="ENROLLED",
    ).select_related("student__user")

    enrolled_count = 0
    for enrollment in enrollments:
        student_user = enrollment.student.user
        if student_user:
            _, created = CandidateAssignment.objects.get_or_create(
                examination=exam,
                student=student_user,
                defaults={"is_eligible": True},
            )
            if created:
                enrolled_count += 1

    exam.status = ExamStatus.PUBLISHED
    exam.save(update_fields=["status", "updated_at"])

    return True, f"Examination published successfully with {enrolled_count} candidates enrolled.", enrolled_count
