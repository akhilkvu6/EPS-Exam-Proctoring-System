"""
Django admin integration for EPS Phoenix custom User model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Administrative management for institutional users.
    """
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "email", "phone", "official_id")},
        ),
        (
            _("Institutional Role & Status"),
            {"fields": ("role", "status", "is_verified")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = (
        "username",
        "first_name",
        "last_name",
        "role",
        "status",
        "is_verified",
        "is_staff",
    )
    list_filter = ("role", "status", "is_verified", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "official_id", "email")
    ordering = ("-date_joined",)
