"""
Concurrency-Safe Roll Number Allocation Service.
Compliant with Section 8.5 (Concurrency safety, database uniqueness, audit history).
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.administration.models import InstitutionSetting
from apps.admissions.models import RollSequenceCounter, RollAllocationRecord
import logging

logger = logging.getLogger(__name__)


class RollAllocationError(Exception):
    """Raised when roll number allocation constraints are violated."""
    pass


def allocate_roll_number_atomic(
    student_profile: StudentProfile,
    allocated_by=None,
    custom_override: str = None,
    prefix_override: str = None,
) -> str:
    """
    Allocates an official institutional roll number sequentially and atomically.

    Guarantees:
    1. Only approved candidates can receive an official roll number.
    2. Concurrency-safe using database row-level locking (select_for_update).
    3. Monotonically increasing sequence without race conditions.
    4. Immutable audit record creation.
    """
    if student_profile.admission_status != AdmissionApplicationStatus.APPROVED:
        raise RollAllocationError(
            f"Cannot allocate official roll number. Candidate {student_profile.registration_number} "
            f"is currently in status '{student_profile.get_admission_status_display()}'. "
            f"Admission approval is strictly required before allocation."
        )

    # If candidate already has an allocated roll number and record, return existing
    if student_profile.roll_number and hasattr(student_profile, "roll_allocation_record"):
        return student_profile.roll_number

    with transaction.atomic():
        settings_obj = InstitutionSetting.get_settings()
        prefix = (prefix_override or settings_obj.roll_number_prefix or "EP").strip().upper()
        current_year = timezone.now().year

        if custom_override:
            formatted_roll = custom_override.strip()
            # Verify uniqueness
            if StudentProfile.objects.filter(roll_number__iexact=formatted_roll).exclude(id=student_profile.id).exists():
                raise RollAllocationError(f"Roll number '{formatted_roll}' is already allocated to another student.")
            format_pattern = "CUSTOM_OVERRIDE"
        else:
            # Concurrency-safe atomic increment with row-level lock
            counter, created = RollSequenceCounter.objects.select_for_update().get_or_create(
                prefix=prefix,
                academic_year=current_year,
                defaults={"current_sequence": 0},
            )
            counter.current_sequence += 1
            counter.save(update_fields=["current_sequence", "updated_at"])

            format_pattern = "{prefix}-{year}-{seq:04d}"
            formatted_roll = f"{prefix}-{current_year}-{counter.current_sequence:04d}"

            # Secondary sanity check against database collision
            while StudentProfile.objects.filter(roll_number__iexact=formatted_roll).exclude(id=student_profile.id).exists():
                counter.current_sequence += 1
                counter.save(update_fields=["current_sequence", "updated_at"])
                formatted_roll = f"{prefix}-{current_year}-{counter.current_sequence:04d}"

        # Assign to student profile
        student_profile.roll_number = formatted_roll
        student_profile.save(update_fields=["roll_number", "updated_at"])

        # Create immutable allocation record
        record, _ = RollAllocationRecord.objects.get_or_create(
            student_profile=student_profile,
            defaults={
                "allocated_roll_number": formatted_roll,
                "allocated_by": allocated_by,
                "format_pattern": format_pattern,
            },
        )

        logger.info(
            f"[ROLL ALLOCATION] Successfully allocated {formatted_roll} to {student_profile.registration_number} "
            f"by {allocated_by.username if allocated_by else 'System'}. Ticket: {record.allocation_ticket_id}"
        )
        return formatted_roll
