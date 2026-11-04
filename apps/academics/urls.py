"""
URL patterns for apps.academics.
"""

from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("departments/", views.departments_list_view, name="departments_list"),
    path("courses/", views.courses_list_view, name="courses_list"),
    path("batches/", views.batches_list_view, name="batches_list"),
    path("subjects/", views.subjects_list_view, name="subjects_list"),
    path("assignments/", views.teacher_assignments_view, name="teacher_assignments"),
]
