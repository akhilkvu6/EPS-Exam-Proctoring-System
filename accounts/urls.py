from django.urls import path
from . import views

urlpatterns = [
    # Common Authentication & Registration
    path('login/', views.common_login, name='common_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('register/', views.central_register, name='register'),
    path('register/central/', views.central_register, name='central_register'),
    path('register/success/', views.registration_success, name='registration_success'),
    path('status/', views.account_status, name='account_status'),
    path('profile/', views.user_profile, name='user_profile'),
    path('change-password/', views.change_password, name='change_password'),

    # In-App Notification Center
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),

    # Student URLs (Legacy & Direct)
    path('student/register/', views.student_register, name='student_register'),
    path('student/register/success/', views.student_registration_success, name='student_registration_success'),
    path('student/login/', views.student_login, name='student_login'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),

    # Teacher URLs (Legacy & Direct)
    path('teacher/register/', views.teacher_register, name='teacher_register'),
    path('teacher/register/success/', views.teacher_registration_success, name='teacher_registration_success'),
    path('teacher/login/', views.teacher_login, name='teacher_login'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/student-approvals/', views.teacher_student_approvals, name='teacher_student_approvals'),
    path('teacher/review-student/<int:student_id>/', views.review_student, name='review_student'),

    # Administrator Portal: Overview & Analytics
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('admin/audit-logs/', views.admin_audit_logs, name='admin_audit_logs'),

    # Administrator Portal: User Management
    path('admin/students/', views.admin_students, name='admin_students'),
    path('admin/student/<int:student_id>/', views.admin_student_detail, name='admin_student_detail'),
    path('admin/teachers/', views.admin_teachers, name='admin_teachers'),
    path('admin/teacher/<int:teacher_id>/', views.admin_teacher_detail, name='admin_teacher_detail'),
    path('admin/student-approvals/', views.admin_student_approvals, name='admin_student_approvals'),
    path('admin/teacher-approvals/', views.admin_teacher_approvals, name='admin_teacher_approvals'),
    path('admin/review-student/<int:student_id>/', views.admin_review_student, name='admin_review_student'),
    path('admin/review-teacher/<int:teacher_id>/', views.review_teacher, name='review_teacher'),
    path('admin/suspended/', views.admin_suspended_accounts, name='admin_suspended_accounts'),
    path('admin/approval-history/', views.admin_approval_history, name='admin_approval_history'),
    path('admin/toggle-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

    # Administrator Portal: Academic Hierarchy
    path('admin/departments/', views.admin_departments, name='admin_departments'),
    path('admin/departments/<int:dept_id>/edit/', views.admin_edit_department, name='admin_edit_department'),
    path('admin/classes/', views.admin_classes, name='admin_classes'),
    path('admin/classes/<int:class_id>/edit/', views.admin_edit_class, name='admin_edit_class'),

    # Administrator Portal: Policies, Backup & Security
    path('admin/policies/', views.admin_policies, name='admin_policies'),
    path('admin/policies/export/', views.admin_policies_export, name='admin_policies_export'),
    path('admin/backup/', views.admin_backup, name='admin_backup'),
    path('admin/security/', views.admin_security, name='admin_security'),

    # Bulk Student Excel Management
    path('students/import/', views.import_students, name='import_students'),
    path('students/import/template/', views.download_student_template, name='download_student_template'),
]