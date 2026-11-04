from django.urls import path
from apps.proctoring import views

app_name = "proctoring"

urlpatterns = [
    path("api/<uuid:attempt_id>/event/", views.api_log_event, name="api_log_event"),
    path("api/<uuid:attempt_id>/status/", views.api_get_proctoring_status, name="api_status"),
]
