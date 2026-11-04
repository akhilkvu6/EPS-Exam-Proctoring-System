"""
Teacher Profile and Admission Review Models for EPS Phoenix.
Compliant with Section 7 (Teacher permissions) and Section 8.3 (Teacher workflow).
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.student.models import StudentProfile


class AdmissionReviewAction(models.TextChoices):
    APPROVE = "APPROVE", _("Approve Admission Application")
    REJECT = "REJECT", _("Reject Application")
    REQUEST_INFO = "REQUEST_INFO", _("Request Additional Information")
    ESCALATE = "ESCALATE", _("Escalate to Institutional Admin")


class TeacherProfile(models.Model):
    """
    Official institutional faculty profile.
    Maintains academic department scoping and staff identification.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    staff_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Official institutional faculty / employee identification number."),
    )
    designation = models.CharField(
        max_length=100,
        default="Assistant Professor",
        help_text=_("Academic faculty title / rank."),
    )
    department_name = models.CharField(
        max_length=120,
        default="Department of Computer Science",
        db_index=True,
        help_text=_("Primary academic department governing admission review and exam scoping."),
    )
    office_location = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_("Campus office building or room number."),
    )
    qualifications = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Academic degrees and credentials (e.g. Ph.D. in Computer Engineering)."),
    )
    is_head_of_department = models.BooleanField(
        default=False,
        help_text=_("Designates departmental head with cross-batch oversight."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Teacher Profile")
        verbose_name_plural = _("Teacher Profiles")
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{self.designation} {full_name} [{self.staff_id}] - {self.department_name}"


class AdmissionReviewRecord(models.Model):
    """
    Immutable audit trail of faculty and administrative admission decisions.
    """
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="review_history",
        help_text=_("Candidate application under review."),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admission_reviews_conducted",
        help_text=_("Faculty member or administrator who recorded this decision."),
    )
    action = models.CharField(
        max_length=30,
        choices=AdmissionReviewAction.choices,
        help_text=_("Institutional action taken."),
    )
    remarks = models.TextField(
        help_text=_("Internal evaluation comments or specific instructions to candidate."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Timestamp of decision."),
    )

    class Meta:
        verbose_name = _("Admission Review Record")
        verbose_name_plural = _("Admission Review Records")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.student_profile.registration_number} by {self.reviewer.username}"
