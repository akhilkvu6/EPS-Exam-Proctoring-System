import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


class InterventionAction(models.TextChoices):
    OFFICIAL_WARNING = "OFFICIAL_WARNING", "Official Candidate Warning"
    EXTEND_TIME = "EXTEND_TIME", "Grant Time Extension"
    MARK_FALSE_POSITIVE = "MARK_FALSE_POSITIVE", "Classify Event as False Positive"
    FORCE_TERMINATE = "FORCE_TERMINATE", "Authorize Security Termination"


class FinalDisposition(models.TextChoices):
    PENDING = "PENDING", "Pending Faculty Adjudication"
    CLEARED = "CLEARED", "Cleared (Integrity Reaffirmed)"
    PENALIZED = "PENALIZED", "Penalized (Mark Deduction Applied)"
    NULLIFIED = "NULLIFIED", "Attempt Annulled"
    ESCALATED_ADMIN = "ESCALATED_ADMIN", "Escalated to Institutional Admin"


class InvigilatorIntervention(models.Model):
    """
    Real-time faculty intervention action recorded against an active candidate attempt.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        "exam_engine.ExamAttempt",
        on_delete=models.CASCADE,
        related_name="interventions",
    )
    invigilator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_interventions",
    )
    action_type = models.CharField(
        max_length=30,
        choices=InterventionAction.choices,
    )
    message_to_candidate = models.TextField(
        blank=True,
        help_text="Urgent notice displayed immediately in the candidate exam room",
    )
    granted_extra_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Additional minutes granted for technical or accessibility reasons",
    )
    notes = models.TextField(blank=True, help_text="Confidential invigilator logs")
    is_acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_action_type_display()}] on Attempt {self.attempt_id} by {self.invigilator}"


class IncidentReviewRecord(models.Model):
    """
    Formal post-examination audit review for attempts flagged with suspicious proctoring events.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.OneToOneField(
        "exam_engine.ExamAttempt",
        on_delete=models.CASCADE,
        related_name="incident_review",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_incidents",
    )
    final_disposition = models.CharField(
        max_length=30,
        choices=FinalDisposition.choices,
        default=FinalDisposition.PENDING,
    )
    penalty_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentage score reduction penalty (0.00% - 100.00%)",
    )
    findings_summary = models.TextField(
        blank=True,
        help_text="Formal factual findings and disciplinary rationale",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    adjudicated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-adjudicated_at"]

    def __str__(self):
        return f"Incident Review for Attempt {self.attempt_id} ({self.get_final_disposition_display()})"
