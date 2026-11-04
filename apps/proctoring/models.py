import uuid
from decimal import Decimal
from django.db import models


class ProctoringEventType(models.TextChoices):
    FULLSCREEN_EXIT = "FULLSCREEN_EXIT", "Fullscreen Exit"
    TAB_SWITCH = "TAB_SWITCH", "Tab Switch / Window Blur"
    CLIPBOARD_COPY = "CLIPBOARD_COPY", "Prohibited Copy Action"
    CLIPBOARD_PASTE = "CLIPBOARD_PASTE", "Prohibited Paste Action"
    DEVTOOLS_ATTEMPT = "DEVTOOLS_ATTEMPT", "Developer Tools Interception"
    WINDOW_RESIZE = "WINDOW_RESIZE", "Suspicious Window Resize"
    SUSPICIOUS_KEY = "SUSPICIOUS_KEY", "Restricted Key Combination"
    AI_ABSENCE = "AI_ABSENCE", "Candidate Absence (Face Undetected)"
    AI_MULTIFACE = "AI_MULTIFACE", "Multiple Faces in Camera Frame"
    AI_GAZE_AWAY = "AI_GAZE_AWAY", "Prolonged Gaze / Head Angle Deviation"
    AI_DEVICE_DETECTED = "AI_DEVICE_DETECTED", "Secondary Electronic Device Visible"


class EventSeverity(models.TextChoices):
    INFO = "INFO", "Informational"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical Incident"


class ProctoringEvent(models.Model):
    """
    Fine-grained integrity event logged during candidate exam attempt.
    Complies with noise-filtering requirements to discard false positives.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        "exam_engine.ExamAttempt",
        on_delete=models.CASCADE,
        related_name="proctoring_events",
    )
    event_type = models.CharField(
        max_length=30,
        choices=ProctoringEventType.choices,
        db_index=True,
    )
    severity = models.CharField(
        max_length=15,
        choices=EventSeverity.choices,
        default=EventSeverity.WARNING,
    )
    duration_seconds = models.FloatField(
        default=0.0,
        help_text="Duration of departure or violation event in seconds",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contextual details (e.g. key combo, screen dimensions)",
    )
    is_noise_filtered = models.BooleanField(
        default=False,
        help_text="True if event fell below minimum duration threshold and discarded from penalties",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["attempt", "event_type"]),
            models.Index(fields=["attempt", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.get_event_type_display()} ({self.duration_seconds}s) - Attempt {self.attempt_id}"


class ProctoringSummary(models.Model):
    """
    Aggregated integrity dossier and real-time Trust Score for an exam attempt.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.OneToOneField(
        "exam_engine.ExamAttempt",
        on_delete=models.CASCADE,
        related_name="proctoring_summary",
    )
    fullscreen_exit_count = models.PositiveIntegerField(default=0)
    tab_switch_count = models.PositiveIntegerField(default=0)
    clipboard_violation_count = models.PositiveIntegerField(default=0)
    total_out_of_focus_seconds = models.FloatField(default=0.0)
    ai_anomaly_count = models.PositiveIntegerField(default=0)
    trust_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text="Dynamic candidate integrity index (0.00 - 100.00)",
    )
    requires_human_review = models.BooleanField(
        default=False,
        help_text="Flagged when trust score drops below threshold or high-severity events occur",
    )
    review_decision = models.CharField(
        max_length=30,
        blank=True,
        help_text="Faculty adjudication verdict (CLEARED, WARNED, PENALIZED, TERMINATED)",
    )
    review_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Proctoring Summaries"

    def __str__(self):
        return f"Trust Score: {self.trust_score}% | Attempt {self.attempt_id} ({'Review Required' if self.requires_human_review else 'Good'})"
