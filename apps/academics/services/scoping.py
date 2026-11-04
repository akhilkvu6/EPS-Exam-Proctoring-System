"""
Academic Scoping and Access Authorization Services for EPS Phoenix.
Compliant with Section 7 (Scoping) and Section 9 (Academic Relationships).
"""

from django.db.models import QuerySet
from apps.accounts.models import User, UserRole
from apps.student.models import StudentProfile
from apps.academics.models import (
    Subject,
    AcademicBatch,
    TeacherAssignment,
    StudentEnrollment,
)
import logging

logger = logging.getLogger(__name__)


def get_teacher_assigned_subjects(user: User) -> QuerySet:
    """
    Returns subjects that the specified faculty member is officially assigned to teach.
    Superusers and Admins receive all subjects.
    """
    if user.is_superuser or user.role == UserRole.ADMIN:
        return Subject.objects.filter(is_active=True)

    assigned_subject_ids = TeacherAssignment.objects.filter(
        teacher=user,
        is_active=True,
    ).values_list("subject_id", flat=True)

    return Subject.objects.filter(id__in=assigned_subject_ids, is_active=True)


def get_teacher_assigned_batches(user: User) -> QuerySet:
    """
    Returns academic cohorts assigned to the specified faculty member.
    """
    if user.is_superuser or user.role == UserRole.ADMIN:
        return AcademicBatch.objects.filter(is_active=True)

    assigned_batch_ids = TeacherAssignment.objects.filter(
        teacher=user,
        is_active=True,
    ).values_list("batch_id", flat=True)

    return AcademicBatch.objects.filter(id__in=assigned_batch_ids, is_active=True)


def is_student_in_teacher_scope(teacher_user: User, student_profile: StudentProfile) -> bool:
    """
    Determines if a candidate is enrolled in any batch/subject assigned to the teacher.
    Guarantees strict server-side academic boundary enforcement per Section 7 & 9.
    """
    if teacher_user.is_superuser or teacher_user.role == UserRole.ADMIN:
        return True

    # Check if student has an active enrollment in any batch assigned to teacher
    if hasattr(student_profile, "academic_enrollment"):
        student_batch = student_profile.academic_enrollment.batch
        return TeacherAssignment.objects.filter(
            teacher=teacher_user,
            batch=student_batch,
            is_active=True,
        ).exists()

    # Fallback to department check if enrollment record not yet initialized
    if hasattr(teacher_user, "teacher_profile"):
        return (
            student_profile.department_name.lower()
            == teacher_user.teacher_profile.department_name.lower()
        )

    return False


def promote_student_semester(student_profile: StudentProfile, target_semester: int = None) -> int:
    """
    Promotes student to next semester level.
    Validates against maximum semesters allowed by the enrolled course program.
    """
    if hasattr(student_profile, "academic_enrollment"):
        enrollment = student_profile.academic_enrollment
        max_semesters = enrollment.batch.course.total_semesters

        next_sem = target_semester if target_semester else enrollment.current_semester + 1
        if next_sem > max_semesters:
            enrollment.status = StudentEnrollment.EnrollmentStatus.GRADUATED
            enrollment.save(update_fields=["status", "updated_at"])
            return enrollment.current_semester

        enrollment.current_semester = next_sem
        enrollment.status = StudentEnrollment.EnrollmentStatus.PROMOTED
        enrollment.save(update_fields=["current_semester", "status", "updated_at"])

        student_profile.current_semester = next_sem
        student_profile.save(update_fields=["current_semester", "updated_at"])
        return next_sem
    else:
        # Fallback for student profile
        next_sem = target_semester if target_semester else student_profile.current_semester + 1
        student_profile.current_semester = next_sem
        student_profile.save(update_fields=["current_semester", "updated_at"])
        return next_sem
