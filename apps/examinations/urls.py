from django.urls import path
from apps.examinations import views

app_name = "examinations"

urlpatterns = [
    path("", views.exam_list_view, name="exam_list"),
    path("create/", views.exam_create_view, name="exam_create"),
    path("<int:pk>/", views.exam_detail_view, name="exam_detail"),
    path("<int:pk>/sections/add/", views.exam_add_section_view, name="exam_add_section"),
    path("<int:exam_pk>/sections/<int:section_pk>/questions/add/", views.exam_add_question_view, name="exam_add_question"),
    path("<int:pk>/publish/", views.exam_publish_view, name="exam_publish"),
    path("<int:pk>/roster/", views.exam_candidate_roster_view, name="exam_roster"),
]
