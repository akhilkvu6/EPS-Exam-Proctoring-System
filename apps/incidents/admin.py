from django.contrib import admin
from apps.incidents.models import InvigilatorIntervention, IncidentReviewRecord


@admin.register(InvigilatorIntervention)
class InvigilatorInterventionAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "invigilator", "action_type", "granted_extra_minutes", "created_at")
    list_filter = ("action_type", "is_acknowledged")
    search_fields = ("attempt__student__username", "invigilator__username", "message_to_candidate")
    readonly_fields = ("id", "created_at")


@admin.register(IncidentReviewRecord)
class IncidentReviewRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "reviewer", "final_disposition", "penalty_percentage", "adjudicated_at")
    list_filter = ("final_disposition",)
    search_fields = ("attempt__student__username", "findings_summary")
