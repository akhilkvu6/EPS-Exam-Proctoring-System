import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


def calculate_grade_letter(percentage: Decimal) -> str:
    """Computes academic grade letter classification."""
    pct = float(percentage)
    if pct >= 90.0:
        return "O"   # Outstanding
    elif pct >= 80.0:
        return "A+"  # Excellent
    elif pct >= 70.0:
        return "A"   # Very Good
    elif pct >= 60.0:
        return "B+"  # Good
    elif pct >= 50.0:
        return "B"   # Above Average
    elif pct >= 40.0:
        return "C"   # Pass
    return "F"       # Fail


class ExaminationResult(models.Model):
    """
    Official published examination scorecard record fortified with a
    cryptographic SHA-256 digital verification hash.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.OneToOneField(
        "exam_engine.ExamAttempt",
        on_delete=models.CASCADE,
        related_name="examination_result",
    )
    examination = models.ForeignKey(
        "examinations.Examination",
        on_delete=models.CASCADE,
        related_name="published_results",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="published_results",
    )
    total_score = models.DecimalField(max_digits=6, decimal_places=2)
    maximum_score = models.DecimalField(max_digits=6, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    grade_letter = models.CharField(max_length=5)
    is_passed = models.BooleanField()
    verification_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Immutable SHA-256 cryptographic verification fingerprint",
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-percentage", "student__username"]
        unique_together = ("examination", "student")

    def __str__(self):
        return f"Result {self.student.username} -> {self.examination.code} ({self.total_score}/{self.maximum_score} - {self.grade_letter})"
