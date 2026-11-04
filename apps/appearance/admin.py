from django.contrib import admin
from apps.appearance.models import UserAppearancePreference


@admin.register(UserAppearancePreference)
class UserAppearancePreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "theme_mode", "accent_color", "density", "high_contrast", "updated_at")
    list_filter = ("theme_mode", "density", "high_contrast")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "updated_at")
