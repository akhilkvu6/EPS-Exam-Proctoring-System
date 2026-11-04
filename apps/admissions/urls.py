"""
URL patterns for apps.admissions.
"""

from django.urls import path
from . import views

app_name = "admissions"

urlpatterns = [
    path("roll-registry/", views.roll_registry_view, name="roll_registry"),
    path("api/status/<str:registration_number>/", views.application_status_api, name="application_status_api"),
]
