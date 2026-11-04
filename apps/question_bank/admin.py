from django.contrib import admin
from apps.question_bank.models import (
    Question,
    QuestionOption,
    QuestionCategory,
    QuestionSnapshot,
)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "question_type", "difficulty", "version", "default_marks", "is_archived")
    list_filter = ("subject", "question_type", "difficulty", "is_archived")
    search_fields = ("title", "content")
    inlines = [QuestionOptionInline]


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "created_at")
    list_filter = ("subject",)
    search_fields = ("name", "description")


@admin.register(QuestionSnapshot)
class QuestionSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "version", "created_at")
    list_filter = ("version", "created_at")
    readonly_fields = ("id", "question", "version", "snapshot_data", "created_at")
