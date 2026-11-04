from django.urls import path
from apps.evaluation import views

app_name = "evaluation"

urlpatterns = [
    path("", views.evaluation_queue_view, name="queue"),
    path("exam/<int:exam_pk>/", views.exam_evaluation_overview_view, name="exam_overview"),
    path("item/<uuid:attempt_q_id>/grade/", views.grade_subjective_item_view, name="grade_item"),
]
