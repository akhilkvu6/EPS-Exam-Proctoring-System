from django.urls import path
from apps.results import views

app_name = "results"

urlpatterns = [
    path("my-results/", views.student_results_list_view, name="my_results"),
    path("scorecard/<uuid:result_id>/", views.scorecard_view, name="scorecard"),
    path("scorecard/<uuid:result_id>/pdf/", views.download_scorecard_pdf_view, name="download_pdf"),
    path("verify/<uuid:result_id>/", views.public_verify_result_view, name="public_verify"),
    path("publish/<int:exam_pk>/", views.publish_results_view, name="publish_results"),
]
