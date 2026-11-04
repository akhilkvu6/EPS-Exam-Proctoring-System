"""
Identity and User Models for EPS Phoenix.
Compliant with Section 7 (Identity, Authentication and Permissions).
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(UserManager):
    """
    Custom user manager ensuring institutional role and status defaults.
    """
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.STUDENT)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        return super().create_user(username, email=email, password=password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", _("Institutional Administrator")
    TEACHER = "TEACHER", _("Teacher / Invigilator")
    STUDENT = "STUDENT", _("Student / Candidate")


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active & Verified")
    PENDING_APPROVAL = "PENDING_APPROVAL", _("Pending Institutional Approval")
    SUSPENDED = "SUSPENDED", _("Suspended by Administration")
    INACTIVE = "INACTIVE", _("Inactive")


class User(AbstractUser):
    """
    Custom user model for EPS Phoenix.
    Decouples institutional identity, username, email, phone, and official IDs.
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        db_index=True,
        help_text=_("Primary institutional role determining workspace permissions."),
    )
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
        help_text=_("Account lifecycle status."),
    )
    # Email and Phone are explicitly optional per Section 7 requirements
    email = models.EmailField(
        _("email address"),
        blank=True,
        null=True,
        help_text=_("Optional institutional or contact email address."),
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Optional contact phone number."),
    )
    official_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Institutional staff ID, applicant registration ID, or internal sequence reference."),
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Indicates whether credentials have been verified by institutional administrators."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["role", "status"]),
            models.Index(fields=["username", "role"]),
        ]

    def __str__(self):
        full_name = self.get_full_name().strip()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def is_admin_user(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_teacher_user(self) -> bool:
        return self.role == UserRole.TEACHER

    @property
    def is_student_user(self) -> bool:
        return self.role == UserRole.STUDENT

    @property
    def is_active_account(self) -> bool:
        return self.is_active and self.status == UserStatus.ACTIVE

    def can_access_workspace(self, workspace_role: str) -> bool:
        """
        Server-side validation of workspace access rights.
        Admin can access administrative areas; superusers can access all.
        """
        if not self.is_active_account:
            return False
        if self.is_superuser:
            return True
        return self.role.upper() == workspace_role.upper()
