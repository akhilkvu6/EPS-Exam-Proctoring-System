"""
Institutional Governance and Audit Models for EPS Phoenix.
Compliant with Section 7 (Admin authority), Section 20 (Branding), and Section 22 (Security).
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class InstitutionSetting(models.Model):
    """
    Singleton institutional settings model governing platform configuration,
    default appearance tokens, and admission policies.
    """
    institution_name = models.CharField(
        max_length=200,
        default="Phoenix Institute of Technology",
        help_text=_("Official institution legal name displayed across transcripts and banners."),
    )
    tagline = models.CharField(
        max_length=255,
        default="Excellence in Academic Integrity & Online Examinations",
        blank=True,
        help_text=_("Institutional motto or descriptive subheading."),
    )
    contact_email = models.EmailField(
        blank=True,
        null=True,
        help_text=_("Central administrative contact email for candidate support."),
    )
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text=_("Central institutional support phone line."),
    )
    default_theme = models.CharField(
        max_length=20,
        choices=[("system", "System Default"), ("light", "Light Mode"), ("dark", "Dark Mode")],
        default="system",
        help_text=_("Default platform appearance theme for non-authenticated portals."),
    )
    default_accent_color = models.CharField(
        max_length=20,
        default="#2563eb",
        help_text=_("Default brand accent color hex code (e.g. #2563eb)."),
    )
    allow_student_self_registration = models.BooleanField(
        default=True,
        help_text=_("Controls whether candidates can submit self-registration applications."),
    )
    roll_number_prefix = models.CharField(
        max_length=20,
        default="EP",
        help_text=_("Default institutional roll number prefix (e.g. EP)."),
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configured_institution_settings",
    )

    class Meta:
        verbose_name = _("Institution Setting")
        verbose_name_plural = _("Institution Settings")

    def __str__(self):
        return f"{self.institution_name} Settings"

    @classmethod
    def get_settings(cls):
        """Retrieves or initializes the institutional singleton instance."""
        instance, created = cls.objects.get_or_create(
            id=1,
            defaults={
                "institution_name": getattr(settings, "INSTITUTION_NAME", "Phoenix Institute of Technology"),
            },
        )
        return instance


class SystemAuditLog(models.Model):
    """
    Chronological security audit trail recording institutional administrative actions.
    """
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions_conducted",
        help_text=_("Administrator or system process executing the action."),
    )
    action_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text=_("Standardized audit action code (e.g. USER_STATUS_CHANGE, ESCALATION_DECISION)."),
    )
    target_repr = models.CharField(
        max_length=255,
        help_text=_("String representation of affected entity or subject."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("Client IP address where request originated."),
    )
    details = models.TextField(
        help_text=_("Comprehensive description of payload or reason for administrative action."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Timestamp when event occurred."),
    )

    class Meta:
        verbose_name = _("System Audit Log")
        verbose_name_plural = _("System Audit Logs")
        ordering = ["-created_at"]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.action_type} by {actor_name} on {self.target_repr}"
