"""
URL patterns for apps.teacher.
"""

from django.urls import path
from . import views

app_name = "teacher"

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("admissions/", views.admission_queue_view, name="admission_queue"),
    path("admissions/<int:application_id>/", views.admission_detail_view, name="admission_detail"),
    path("students/", views.students_list_view, name="students_list"),
    path("profile/", views.profile_view, name="profile"),
]
