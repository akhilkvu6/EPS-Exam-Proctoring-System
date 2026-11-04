"""
Django admin integration for apps.administration models.
"""

from django.contrib import admin
from .models import InstitutionSetting, SystemAuditLog


@admin.register(InstitutionSetting)
class InstitutionSettingAdmin(admin.ModelAdmin):
    list_display = (
        "institution_name",
        "default_theme",
        "roll_number_prefix",
        "allow_student_self_registration",
        "updated_at",
    )


@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action_type",
        "actor",
        "target_repr",
        "ip_address",
        "created_at",
    )
    list_filter = ("action_type", "created_at")
    search_fields = ("action_type", "target_repr", "actor__username", "details")
    readonly_fields = ("actor", "action_type", "target_repr", "ip_address", "details", "created_at")
