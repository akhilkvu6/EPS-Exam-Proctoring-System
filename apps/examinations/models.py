import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class ExamStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft Configuration"
    CONFIGURED = "CONFIGURED", "Questions Configured"
    PUBLISHED = "PUBLISHED", "Published & Scheduled"
    ACTIVE = "ACTIVE", "Active (In Progress)"
    CLOSED = "CLOSED", "Closed (Submissions Ended)"
    EVALUATION = "EVALUATION", "Evaluation In Progress"
    RESULTS_PUBLISHED = "RESULTS_PUBLISHED", "Results Published"
    CANCELLED = "CANCELLED", "Cancelled"


class Examination(models.Model):
    title = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Institutional exam code (e.g. EXAM-2026-CS301-MID)",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="examinations",
    )
    batch = models.ForeignKey(
        "academics.AcademicBatch",
        on_delete=models.CASCADE,
        related_name="examinations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_examinations",
    )
    status = models.CharField(
        max_length=25,
        choices=ExamStatus.choices,
        default=ExamStatus.DRAFT,
        db_index=True,
    )
    start_window = models.DateTimeField(
        help_text="Earliest time candidates can launch the examination",
    )
    end_window = models.DateTimeField(
        help_text="Absolute deadline after which no exam session may be active",
    )
    duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Individual candidate session timer in minutes",
    )
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    pass_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("40.00"),
    )
    allow_late_join_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Leniency buffer past start_window to enter exam room",
    )
    shuffle_questions = models.BooleanField(
        default=True,
        help_text="Randomize question sequence per candidate attempt",
    )
    shuffle_options = models.BooleanField(
        default=True,
        help_text="Randomize option sequence per candidate attempt",
    )
    calculator_enabled = models.BooleanField(
        default=False,
        help_text="Enable on-screen scientific calculator",
    )
    strict_proctoring = models.BooleanField(
        default=True,
        help_text="Enforce browser full-screen lock and computer vision monitoring",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Guidelines and rules displayed to candidate prior to launch",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_window", "-created_at"]
        indexes = [
            models.Index(fields=["status", "start_window"]),
            models.Index(fields=["batch", "subject"]),
        ]

    def __str__(self):
        return f"[{self.code}] {self.title} ({self.get_status_display()})"

    def recalculate_total_marks(self):
        """Sums marks from all assigned exam questions and persists total."""
        total = sum(
            eq.marks
            for section in self.sections.all()
            for eq in section.exam_questions.all()
        )
        self.total_marks = total
        self.save(update_fields=["total_marks"])
        return total

    def is_currently_open(self):
        now = timezone.now()
        return self.status in [ExamStatus.PUBLISHED, ExamStatus.ACTIVE] and (
            self.start_window <= now <= self.end_window
        )


class ExamSection(models.Model):
    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(
        max_length=150,
        help_text="Section name, e.g. 'Section A: Multiple Choice'",
    )
    order = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("examination", "title")

    def __str__(self):
        return f"{self.examination.code} - {self.title}"


class ExamQuestion(models.Model):
    section = models.ForeignKey(
        ExamSection,
        on_delete=models.CASCADE,
        related_name="exam_questions",
    )
    question = models.ForeignKey(
        "question_bank.Question",
        on_delete=models.CASCADE,
        related_name="exam_references",
    )
    snapshot = models.ForeignKey(
        "question_bank.QuestionSnapshot",
        on_delete=models.PROTECT,
        related_name="exam_references",
        help_text="Immutable snapshot locked at the time question is added to examination",
    )
    order = models.PositiveIntegerField(default=1)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    negative_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("section", "question")

    def __str__(self):
        return f"Sec {self.section.order} Q{self.order}: {self.question.title} ({self.marks}m)"


class CandidateAssignment(models.Model):
    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name="assigned_candidates",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_assignments",
    )
    is_eligible = models.BooleanField(
        default=True,
        help_text="Toggled off by faculty/admin if student is disqualified or barred",
    )
    disqualification_reason = models.CharField(max_length=255, blank=True)
    extra_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Accommodated or invigilator-granted extra minutes for this candidate",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student__username"]
        unique_together = ("examination", "student")

    def __str__(self):
        return f"{self.student.username} -> {self.examination.code} ({'Eligible' if self.is_eligible else 'Disqualified'})"
