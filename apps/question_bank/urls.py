from django.urls import path
from apps.question_bank import views

app_name = "question_bank"

urlpatterns = [
    path("", views.question_list_view, name="question_list"),
    path("create/", views.question_create_view, name="question_create"),
    path("<int:pk>/", views.question_detail_view, name="question_detail"),
    path("<int:pk>/edit/", views.question_edit_view, name="question_edit"),
    path("<int:pk>/duplicate/", views.question_duplicate_view, name="question_duplicate"),
    path("<int:pk>/archive/", views.question_archive_view, name="question_archive"),
]
