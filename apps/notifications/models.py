import uuid
from django.conf import settings
from django.db import models


class NotificationLevel(models.TextChoices):
    INFO = "INFO", "Informational"
    SUCCESS = "SUCCESS", "Success"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical Alert"


class Notification(models.Model):
    """
    In-app notification entity providing real-time event feeds without
    mandatory paid third-party SMS or email dependencies.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    level = models.CharField(
        max_length=15,
        choices=NotificationLevel.choices,
        default=NotificationLevel.INFO,
    )
    action_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional relative navigation link when notification is clicked",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.level}] {self.recipient.username}: {self.title}"
