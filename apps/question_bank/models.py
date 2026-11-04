import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


class QuestionType(models.TextChoices):
    MCQ_SINGLE = "MCQ_SINGLE", "Single Choice Objective"
    MCQ_MULTI = "MCQ_MULTI", "Multiple Choice Objective"
    TRUE_FALSE = "TRUE_FALSE", "True / False"
    FILL_BLANKS = "FILL_BLANKS", "Fill in the Blanks"
    NUMERICAL = "NUMERICAL", "Numerical Value"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"
    DESCRIPTIVE = "DESCRIPTIVE", "Descriptive / Essay"
    IMAGE_BASED = "IMAGE_BASED", "Image-Based Prompt"


class QuestionDifficulty(models.TextChoices):
    EASY = "EASY", "Easy"
    MEDIUM = "MEDIUM", "Medium"
    HARD = "HARD", "Hard"


class QuestionCategory(models.Model):
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="question_categories",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Question Categories"
        unique_together = ("subject", "name")
        ordering = ["subject", "name"]

    def __str__(self):
        return f"{self.subject.code} - {self.name}"


class Question(models.Model):
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    category = models.ForeignKey(
        QuestionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_questions",
    )
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MCQ_SINGLE,
    )
    difficulty = models.CharField(
        max_length=10,
        choices=QuestionDifficulty.choices,
        default=QuestionDifficulty.MEDIUM,
    )
    title = models.CharField(
        max_length=255,
        help_text="Short descriptive label for question management",
    )
    content = models.TextField(
        help_text="Primary question text or prompt (supports markdown)",
    )
    image = models.ImageField(
        upload_to="questions/diagrams/",
        null=True,
        blank=True,
        help_text="Optional diagram or figure for visual/image-based questions",
    )
    default_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.00"),
    )
    negative_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    explanation = models.TextField(
        blank=True,
        help_text="Pedagogical rationale or model solution (hidden from active candidates)",
    )
    rubric = models.TextField(
        blank=True,
        help_text="Evaluation criteria and grading rubric for subjective questions",
    )
    numerical_target = models.FloatField(
        null=True,
        blank=True,
        help_text="Target numerical value for numerical items",
    )
    numerical_tolerance = models.FloatField(
        default=0.0,
        help_text="Acceptable absolute +/- deviation from the target value",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Monotonically incremented version index on modifications",
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Soft-archived questions are excluded from future exam authoring",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["subject", "question_type"]),
            models.Index(fields=["subject", "difficulty"]),
            models.Index(fields=["is_archived"]),
        ]

    def __str__(self):
        return f"[{self.subject.code}] {self.title} (v{self.version})"


class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Option {self.order} for Question {self.question_id} ({'Correct' if self.is_correct else 'Incorrect'})"


class QuestionSnapshot(models.Model):
    """
    Immutable frozen snapshot of a Question and its options at an exact version.
    Examinations associate with snapshots, preventing retrospective changes from
    corrupting ongoing or completed examination attempts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    version = models.PositiveIntegerField()
    snapshot_data = models.JSONField(
        help_text="Full immutable state representation of the question at capture time",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("question", "version")
        ordering = ["-version"]

    def __str__(self):
        return f"Snapshot Question #{self.question_id} v{self.version} ({self.id})"
