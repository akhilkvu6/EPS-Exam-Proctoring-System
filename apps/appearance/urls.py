from django.urls import path
from apps.appearance import views

app_name = "appearance"

urlpatterns = [
    path("settings/", views.appearance_settings_view, name="settings"),
    path("api/update/", views.api_update_appearance, name="api_update"),
]
