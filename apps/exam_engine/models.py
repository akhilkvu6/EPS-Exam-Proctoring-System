import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SUBMITTED = "SUBMITTED", "Submitted by Candidate"
    AUTO_SUBMITTED = "AUTO_SUBMITTED", "Auto-Submitted on Timeout"
    EVALUATED = "EVALUATED", "Evaluated & Graded"
    TERMINATED_SECURITY = "TERMINATED_SECURITY", "Terminated for Security Breach"


class ExamAttempt(models.Model):
    """
    Candidate Examination Attempt entity enforcing server-authoritative timers
    and cryptographic submission receipts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    examination = models.ForeignKey(
        "examinations.Examination",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_attempts",
    )
    status = models.CharField(
        max_length=30,
        choices=AttemptStatus.choices,
        default=AttemptStatus.IN_PROGRESS,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Server-authoritative hard expiration timestamp",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    total_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    submission_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 cryptographic proof of submission",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("examination", "student")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"Attempt {self.id} | {self.student.username} -> {self.examination.code} ({self.status})"

    def is_expired(self) -> bool:
        """Server-authoritative expiration check."""
        return timezone.now() >= self.expires_at

    def get_remaining_seconds(self) -> int:
        """Returns integer seconds remaining on server clock. Clamped at 0."""
        if self.status != AttemptStatus.IN_PROGRESS:
            return 0
        diff = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(diff))


class AttemptQuestion(models.Model):
    """
    Individual question delivery item attached to an attempt.
    Holds sanitized student-safe payload and candidate's response.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="attempt_questions",
    )
    exam_question = models.ForeignKey(
        "examinations.ExamQuestion",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    order = models.PositiveIntegerField()
    safe_payload = models.JSONField(
        help_text="Zero-leakage sanitized question data payload",
    )
    candidate_answer = models.JSONField(
        default=dict,
        blank=True,
        help_text="Serialized candidate answer payload",
    )
    is_answered = models.BooleanField(default=False)
    is_flagged_for_review = models.BooleanField(default=False)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    awarded_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_evaluated = models.BooleanField(default=False)
    evaluator_feedback = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("attempt", "exam_question")

    def __str__(self):
        return f"Attempt {self.attempt_id} Q#{self.order} ({'Answered' if self.is_answered else 'Unanswered'})"
