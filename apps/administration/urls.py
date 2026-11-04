"""
URL patterns for apps.administration.
"""

from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("escalations/", views.escalated_admissions_view, name="escalated_admissions"),
    path("escalations/<int:application_id>/", views.escalation_detail_view, name="escalation_detail"),
    path("users/", views.users_directory_view, name="users_directory"),
    path("users/<int:user_id>/status/", views.user_status_toggle_view, name="user_status_toggle"),
    path("teachers/", views.teachers_management_view, name="teachers_management"),
    path("settings/", views.settings_view, name="settings"),
    path("audit-logs/", views.audit_logs_view, name="audit_logs"),
]
