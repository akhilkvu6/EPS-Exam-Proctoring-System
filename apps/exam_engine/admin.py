from django.contrib import admin
from apps.exam_engine.models import ExamAttempt, AttemptQuestion


class AttemptQuestionInline(admin.TabularInline):
    model = AttemptQuestion
    extra = 0
    fields = ("order", "is_answered", "is_flagged_for_review", "time_spent_seconds", "awarded_marks", "is_evaluated")
    readonly_fields = ("order", "safe_payload", "candidate_answer")


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "examination", "status", "started_at", "expires_at", "submitted_at")
    list_filter = ("status", "examination")
    search_fields = ("student__username", "examination__code", "submission_hash")
    readonly_fields = ("id", "started_at", "submission_hash")
    inlines = [AttemptQuestionInline]


@admin.register(AttemptQuestion)
class AttemptQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "order", "is_answered", "is_flagged_for_review", "awarded_marks")
    list_filter = ("is_answered", "is_flagged_for_review", "is_evaluated")
