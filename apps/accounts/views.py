"""
Authentication and identity views for EPS Phoenix.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from .forms import LoginForm
from .models import UserRole, UserStatus
import logging

logger = logging.getLogger(__name__)


def get_role_dashboard_url(user) -> str:
    """
    Computes canonical redirect target based on user's institutional role.
    """
    if user.status == UserStatus.PENDING_APPROVAL:
        return "/accounts/status/"
    if user.status == UserStatus.SUSPENDED:
        return "/accounts/status/"

    if user.role == UserRole.STUDENT:
        return "/student/dashboard/"
    elif user.role == UserRole.TEACHER:
        return "/teacher/dashboard/"
    elif user.role == UserRole.ADMIN or user.is_superuser:
        return "/admin/dashboard/"

    return "/"


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Unified institutional authentication view with role tab selection.
    """
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_url(request.user))

    requested_role = request.GET.get("role", "").upper()
    if requested_role not in [UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN]:
        requested_role = ""

    redirect_to = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)

            messages.success(
                request,
                f"Welcome back, {user.get_full_name() or user.username}!",
            )

            # Validate redirect URL against allowed hosts
            if redirect_to and url_has_allowed_host_and_scheme(
                url=redirect_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(redirect_to)

            return redirect(get_role_dashboard_url(user))
    else:
        form = LoginForm(initial={"intended_role": requested_role})

    context = {
        "form": form,
        "selected_role": requested_role,
        "next": redirect_to,
        "title": "Institutional Sign In",
    }
    return render(request, "accounts/login.html", context)


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Terminates session and clears credentials.
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.info(request, "You have been successfully signed out.")
        logger.info(f"User {username} signed out successfully.")
    return redirect("accounts:login")


def account_status_view(request):
    """
    Displays institutional status for users awaiting review or suspended.
    """
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    context = {
        "user_obj": request.user,
        "title": "Account Status",
    }
    return render(request, "accounts/account_status.html", context)


def access_denied_view(request):
    """
    Friendly institutional access denied explanation.
    """
    context = {
        "title": "Access Denied",
    }
    return render(request, "accounts/access_denied.html", context, status=403)
