from django.contrib import admin
from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'exam', 'total_marks_obtained', 'maximum_marks',
        'percentage', 'is_passed', 'is_published', 'grading_status'
    )
    list_filter = ('is_published', 'is_passed', 'grading_status', 'exam')
    search_fields = ('student__username', 'exam__title')
