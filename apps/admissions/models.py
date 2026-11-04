"""
Admissions and Concurrency-Safe Roll Allocation Models for EPS Phoenix.
Compliant with Section 8.5 (Concurrency-safe Roll allocation, audit history, uniqueness).
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.student.models import StudentProfile
import uuid


class RollSequenceCounter(models.Model):
    """
    Dedicated atomic counter for sequential roll number allocation.
    Utilizes database row-level locking (select_for_update) to guarantee
    zero race conditions during concurrent admission approvals.
    """
    prefix = models.CharField(
        max_length=20,
        default="EP",
        help_text=_("Department or institutional prefix (e.g. EP, CS, ME)."),
    )
    academic_year = models.PositiveIntegerField(
        help_text=_("Four-digit academic calendar year (e.g. 2026)."),
    )
    current_sequence = models.PositiveIntegerField(
        default=0,
        help_text=_("Current monotonically increasing sequence number."),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Roll Sequence Counter")
        verbose_name_plural = _("Roll Sequence Counters")
        unique_together = ("prefix", "academic_year")

    def __str__(self):
        return f"[{self.prefix}-{self.academic_year}] Sequence: {self.current_sequence}"


class RollAllocationRecord(models.Model):
    """
    Immutable audit ledger certifying the official roll number allocation.
    Stores cryptographic UUID ticket and timestamp.
    """
    student_profile = models.OneToOneField(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="roll_allocation_record",
        help_text=_("Enrolled student receiving the roll number."),
    )
    allocated_roll_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Official allocated roll number adhering to institutional format."),
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roll_numbers_authorized",
        help_text=_("Faculty member or administrator who authorized final approval."),
    )
    allocation_ticket_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("Cryptographically secure unique ticket for allocation verification."),
    )
    format_pattern = models.CharField(
        max_length=100,
        default="{prefix}-{year}-{seq:04d}",
        help_text=_("Formatting template used during allocation."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Timestamp of sequential roll number generation."),
    )

    class Meta:
        verbose_name = _("Roll Allocation Record")
        verbose_name_plural = _("Roll Allocation Records")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.allocated_roll_number} -> {self.student_profile.registration_number}"


class AdmissionSupportingDocument(models.Model):
    """
    Optional applicant credentials, mark sheets, or identity certificates.
    """
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="supporting_documents",
    )
    document_title = models.CharField(
        max_length=150,
        help_text=_("e.g. Higher Secondary Marksheet, Identity Proof"),
    )
    document_file = models.FileField(
        upload_to="admissions/documents/%Y/%m/",
        help_text=_("Restricted document attachment."),
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Verified by department faculty during screening."),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Supporting Document")
        verbose_name_plural = _("Supporting Documents")
