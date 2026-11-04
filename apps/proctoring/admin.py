from django.contrib import admin
from apps.proctoring.models import ProctoringEvent, ProctoringSummary


@admin.register(ProctoringEvent)
class ProctoringEventAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "event_type", "severity", "duration_seconds", "is_noise_filtered", "timestamp")
    list_filter = ("event_type", "severity", "is_noise_filtered")
    search_fields = ("attempt__student__username", "attempt__examination__code")
    readonly_fields = ("id", "timestamp")


@admin.register(ProctoringSummary)
class ProctoringSummaryAdmin(admin.ModelAdmin):
    list_display = ("attempt", "trust_score", "fullscreen_exit_count", "tab_switch_count", "total_out_of_focus_seconds", "requires_human_review")
    list_filter = ("requires_human_review", "review_decision")
    search_fields = ("attempt__student__username", "attempt__examination__code")
