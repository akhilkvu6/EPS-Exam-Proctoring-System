from django.urls import path
from apps.exam_engine import views

app_name = "exam_engine"

urlpatterns = [
    path("lobby/<str:exam_code>/", views.exam_lobby_view, name="exam_lobby"),
    path("room/<uuid:attempt_id>/", views.exam_room_view, name="exam_room"),
    path("receipt/<uuid:attempt_id>/", views.exam_receipt_view, name="exam_receipt"),
    # APIs
    path("api/<uuid:attempt_id>/timer/", views.api_get_timer, name="api_timer"),
    path("api/<uuid:attempt_id>/questions/<uuid:question_id>/save/", views.api_save_answer, name="api_save_answer"),
    path("api/<uuid:attempt_id>/questions/<uuid:question_id>/flag/", views.api_toggle_flag, name="api_toggle_flag"),
    path("api/<uuid:attempt_id>/submit/", views.api_submit_exam, name="api_submit"),
]
