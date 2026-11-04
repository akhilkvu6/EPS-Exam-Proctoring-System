"""
Core views for EPS Phoenix.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def index(request):
    """
    Institutional landing page and portal directory.
    """
    context = {
        "title": "Welcome to EPS Phoenix",
        "workspaces": [
            {
                "title": "Student Workspace",
                "role": "student",
                "description": "Access your enrolled examinations, active exam sessions, submission receipts, and published scorecards.",
                "url": "/accounts/login/?role=student",
                "badge": "Exams & Results",
            },
            {
                "title": "Teacher Workspace",
                "role": "teacher",
                "description": "Manage question banks, schedule examinations, invigilate live sessions, review incidents, and evaluate answers.",
                "url": "/accounts/login/?role=teacher",
                "badge": "Evaluation & Proctoring",
            },
            {
                "title": "Admin Workspace",
                "role": "admin",
                "description": "Oversee academic departments, student admissions, staff approvals, institutional settings, and security audits.",
                "url": "/accounts/login/?role=admin",
                "badge": "Governance",
            },
        ],
    }
    return render(request, "core/index.html", context)


def health_check(request):
    """
    Production health check verifying database and application state.
    """
    db_healthy = True
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            if not row or row[0] != 1:
                db_healthy = False
                db_error = "Database returned invalid response"
    except Exception as exc:
        db_healthy = False
        db_error = str(exc)

    status_code = 200 if db_healthy else 503
    return JsonResponse(
        {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "database_error": db_error,
            "platform": getattr(settings, "PLATFORM_NAME", "EPS Phoenix"),
            "version": getattr(settings, "PLATFORM_VERSION", "3.0.0"),
        },
        status=status_code,
    )


def error_400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
