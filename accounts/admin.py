from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TeacherProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'employee_id',
        'department',
        'qualification',
        'verification_status',
    )

    list_filter = (
        'verification_status',
        'department',
    )

    search_fields = (
        'user__username',
        'user__email',
        'employee_id',
    )