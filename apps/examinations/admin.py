from django.contrib import admin
from apps.examinations.models import (
    Examination,
    ExamSection,
    ExamQuestion,
    CandidateAssignment,
)


class ExamSectionInline(admin.TabularInline):
    model = ExamSection
    extra = 1


class CandidateAssignmentInline(admin.TabularInline):
    model = CandidateAssignment
    extra = 0
    readonly_fields = ("assigned_at",)


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "subject", "batch", "status", "start_window", "end_window", "total_marks")
    list_filter = ("status", "subject", "batch")
    search_fields = ("code", "title")
    inlines = [ExamSectionInline, CandidateAssignmentInline]


@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "examination", "order")
    list_filter = ("examination",)


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "section", "snapshot", "order", "marks", "negative_marks")
    list_filter = ("section__examination",)


@admin.register(CandidateAssignment)
class CandidateAssignmentAdmin(admin.ModelAdmin):
    list_display = ("student", "examination", "is_eligible", "extra_time_minutes", "assigned_at")
    list_filter = ("examination", "is_eligible")
    search_fields = ("student__username", "examination__code")
