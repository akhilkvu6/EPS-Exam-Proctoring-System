import uuid
from django.conf import settings
from django.db import models


class ThemeMode(models.TextChoices):
    SYSTEM = "SYSTEM", "System Default (Auto)"
    LIGHT = "LIGHT", "Light Mode"
    DARK = "DARK", "Dark Mode"


class InterfaceDensity(models.TextChoices):
    COMFORTABLE = "COMFORTABLE", "Comfortable (Standard)"
    COMPACT = "COMPACT", "Compact (High Density)"
    RELAXED = "RELAXED", "Relaxed (Spacious)"


class UserAppearancePreference(models.Model):
    """
    ChatGPT-inspired user personalization settings governing color themes,
    accent hues, contrast modes, and spacing density.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appearance_preference",
    )
    theme_mode = models.CharField(
        max_length=15,
        choices=ThemeMode.choices,
        default=ThemeMode.SYSTEM,
    )
    accent_color = models.CharField(
        max_length=20,
        default="#3b82f6",
        help_text="Hex code of the chosen primary brand accent color",
    )
    density = models.CharField(
        max_length=20,
        choices=InterfaceDensity.choices,
        default=InterfaceDensity.COMFORTABLE,
    )
    high_contrast = models.BooleanField(
        default=False,
        help_text="Enhanced contrast ratio for high-visibility accessibility",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Appearance: {self.theme_mode} ({self.accent_color})"
