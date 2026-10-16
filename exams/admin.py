from django.contrib import admin
from .models import Subject, Question, AnswerOption, Exam, ExamQuestion


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'subject', 'question_type', 'difficulty', 'marks', 'negative_marks', 'created_at')
    list_filter = ('subject', 'question_type', 'difficulty')
    search_fields = ('question_text', 'topic')
    inlines = [AnswerOptionInline]


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'start_time', 'end_time', 'duration_minutes', 'total_marks', 'status')
    list_filter = ('status', 'subject', 'camera_required', 'fullscreen_required')
    search_fields = ('title', 'description')
    inlines = [ExamQuestionInline]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'created_at')
    search_fields = ('name', 'code')
