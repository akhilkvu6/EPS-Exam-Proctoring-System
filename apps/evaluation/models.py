import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


class EvaluationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Evaluation"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Fully Evaluated & Finalized"


class EvaluationBatch(models.Model):
    """
    Cohort-level evaluation workflow manager tracking auto-grader execution
    and pending subjective rubric grading queues.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    examination = models.ForeignKey(
        "examinations.Examination",
        on_delete=models.CASCADE,
        related_name="evaluation_batches",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluated_batches",
    )
    status = models.CharField(
        max_length=20,
        choices=EvaluationStatus.choices,
        default=EvaluationStatus.PENDING,
        db_index=True,
    )
    total_attempts = models.PositiveIntegerField(default=0)
    graded_attempts = models.PositiveIntegerField(default=0)
    pending_subjective_items = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Evaluation Batches"

    def __str__(self):
        return f"Evaluation Batch for {self.examination.code} ({self.get_status_display()})"
