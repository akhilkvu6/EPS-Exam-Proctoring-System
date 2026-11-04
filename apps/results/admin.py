from django.contrib import admin
from apps.results.models import ExaminationResult


@admin.register(ExaminationResult)
class ExaminationResultAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "examination", "total_score", "maximum_score", "percentage", "grade_letter", "is_passed", "published_at")
    list_filter = ("grade_letter", "is_passed", "is_published")
    search_fields = ("student__username", "examination__code", "verification_hash")
    readonly_fields = ("id", "verification_hash", "published_at")
