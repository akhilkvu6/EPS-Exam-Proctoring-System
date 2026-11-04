from django.urls import path
from apps.incidents import views

app_name = "incidents"

urlpatterns = [
    path("console/<int:exam_pk>/", views.live_invigilator_console, name="live_console"),
    path("attempt/<uuid:attempt_id>/action/", views.invigilator_action_view, name="invigilator_action"),
    path("api/alerts/<uuid:attempt_id>/", views.api_poll_candidate_alerts, name="api_candidate_alerts"),
]
