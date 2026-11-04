"""
URL patterns for apps.student.
"""

from django.urls import path
from . import views

app_name = "student"

urlpatterns = [
    path("register/", views.student_register, name="register"),
    path("admission-status/", views.admission_status_view, name="admission_status"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("academics/", views.academics_view, name="academics"),
    path("exams/", views.exams_list_view, name="exams_list"),
    path("results/", views.results_list_view, name="results_list"),
]
