from django.contrib import admin
from apps.evaluation.models import EvaluationBatch


@admin.register(EvaluationBatch)
class EvaluationBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "examination", "evaluator", "status", "total_attempts", "graded_attempts", "pending_subjective_items")
    list_filter = ("status",)
    search_fields = ("examination__code", "evaluator__username")
