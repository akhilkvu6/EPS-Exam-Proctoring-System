"""
Root URL configuration for EPS Phoenix.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("student/", include("apps.student.urls", namespace="student")),
    path("teacher/", include("apps.teacher.urls", namespace="teacher")),
    path("administration/", include("apps.administration.urls", namespace="administration")),
    path("admissions/", include("apps.admissions.urls", namespace="admissions")),
    path("academics/", include("apps.academics.urls", namespace="academics")),
    path("questions/", include("apps.question_bank.urls", namespace="question_bank")),
    path("examinations/", include("apps.examinations.urls", namespace="examinations")),
    path("exam/", include("apps.exam_engine.urls", namespace="exam_engine")),
    path("proctoring/", include("apps.proctoring.urls", namespace="proctoring")),
    path("incidents/", include("apps.incidents.urls", namespace="incidents")),
    path("", include("apps.core.urls", namespace="core")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "apps.core.views.error_400"
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
