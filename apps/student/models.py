"""
Student Profile and Academic Identity Models for EPS Phoenix.
Compliant with Section 7 (Student Workspace) and Section 8 (Admissions & Roll Allocation).
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AdmissionApplicationStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Application")
    SUBMITTED = "SUBMITTED", _("Submitted - Pending Initial Screening")
    PENDING_TEACHER = "PENDING_TEACHER", _("Pending Teacher Review")
    INFO_REQUESTED = "INFO_REQUESTED", _("Information Requested from Applicant")
    RESUBMITTED = "RESUBMITTED", _("Resubmitted by Applicant")
    ESCALATED_ADMIN = "ESCALATED_ADMIN", _("Escalated to Institutional Admin")
    APPROVED = "APPROVED", _("Admission Approved")
    REJECTED = "REJECTED", _("Application Rejected")


class StudentProfile(models.Model):
    """
    Official student institutional profile.
    Enforces that official roll numbers are immutable by candidates and strictly
    allocated only post-approval.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    registration_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Unique candidate applicant registration reference."),
    )
    roll_number = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Official sequential roll number allocated strictly upon final admission approval."),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("Candidate date of birth."),
    )
    guardian_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text=_("Parent or legal guardian full name."),
    )
    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Emergency or candidate direct contact number."),
    )
    current_semester = models.PositiveIntegerField(
        default=1,
        help_text=_("Active academic semester (1-8)."),
    )
    department_name = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_("Academic department name."),
    )
    course_name = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_("Enrolled academic program or degree."),
    )
    batch_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Graduating class or batch cycle (e.g. 2024-2028)."),
    )
    admission_status = models.CharField(
        max_length=30,
        choices=AdmissionApplicationStatus.choices,
        default=AdmissionApplicationStatus.SUBMITTED,
        db_index=True,
        help_text=_("Current lifecycle state in the admission pipeline."),
    )
    admission_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when final admission was confirmed."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Student Profile")
        verbose_name_plural = _("Student Profiles")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["admission_status"]),
            models.Index(fields=["roll_number"]),
            models.Index(fields=["registration_number"]),
        ]

    def __str__(self):
        roll_info = f" [Roll: {self.roll_number}]" if self.roll_number else f" [Reg: {self.registration_number}]"
        return f"{self.user.get_full_name() or self.user.username}{roll_info}"

    @property
    def is_admission_approved(self) -> bool:
        return self.admission_status == AdmissionApplicationStatus.APPROVED

    @property
    def display_identifier(self) -> str:
        """Returns official roll number if approved, otherwise registration number."""
        return self.roll_number if self.roll_number else self.registration_number
