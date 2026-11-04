from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, TeacherProfile, StudentProfile, Department, Course,
    AcademicBatch, RollNumberReservation, StudentSemesterHistory,
    StudentEnrollment, ClassGroup, Notification, ApprovalRecord, AuditLog
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role & EPS Settings', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & EPS Settings', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'qualification', 'verification_status', 'reviewed_by', 'reviewed_at')
    list_filter = ('verification_status', 'department')
    search_fields = ('user__username', 'user__email', 'employee_id')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'roll_number', 'department', 'semester', 'class_group', 'verification_status', 'reviewed_by')
    list_filter = ('verification_status', 'department', 'semester')
    search_fields = ('user__username', 'full_name', 'roll_number')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'semester', 'created_at')
    list_filter = ('department', 'semester')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title', 'message')


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'role', 'decision', 'reviewed_by', 'created_at')
    list_filter = ('role', 'decision')
    search_fields = ('applicant__username', 'reason')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'target_user', 'ip_address')
    list_filter = ('action',)
    search_fields = ('actor__username', 'target_user__username', 'details')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'total_semesters', 'created_at')
    list_filter = ('department',)
    search_fields = ('name', 'code')


@admin.register(AcademicBatch)
class AcademicBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_name', 'course', 'admission_year', 'prefix', 'capacity', 'current_semester', 'enrollment_status', 'is_active')
    list_filter = ('admission_year', 'course', 'enrollment_status', 'is_active')
    search_fields = ('batch_name', 'prefix', 'course__name')


@admin.register(RollNumberReservation)
class RollNumberReservationAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'batch', 'roll_sequence', 'status', 'reserved_by_name', 'expires_at')
    list_filter = ('status', 'batch')
    search_fields = ('registration_number', 'reserved_by_email', 'reserved_by_name')


@admin.register(StudentSemesterHistory)
class StudentSemesterHistoryAdmin(admin.ModelAdmin):
    list_display = ('student', 'batch', 'previous_semester', 'new_semester', 'academic_session', 'changed_by', 'created_at')
    search_fields = ('student__roll_number', 'academic_session')


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'full_name', 'course', 'batch', 'semester', 'is_active', 'is_registered')
    list_filter = ('is_active', 'is_registered', 'course', 'batch')
    search_fields = ('roll_number', 'full_name', 'email')
