"""
Security decorators enforcing server-side role boundaries.
Compliant with Section 7 (Server-side authorization).
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from .models import UserRole, UserStatus


def active_user_required(view_func):
    """
    Ensures the user is authenticated and their account status is ACTIVE.
    Redirects pending/suspended users with an informative institutional message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.status == UserStatus.PENDING_APPROVAL:
            messages.warning(
                request,
                "Your registration is currently pending institutional approval. You will receive access once reviewed.",
            )
            return redirect("accounts:account_status")
        if request.user.status == UserStatus.SUSPENDED:
            messages.error(
                request,
                "Your account has been suspended by institutional administration. Please contact the administrative office.",
            )
            return redirect("accounts:account_status")
        if not request.user.is_active:
            raise PermissionDenied("Your account is currently disabled.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles):
    """
    Generic decorator requiring one of the specified institutional roles.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if not request.user.is_active_account:
                return active_user_required(view_func)(request, *args, **kwargs)
            if request.user.role not in allowed_roles:
                raise PermissionDenied(
                    f"Access restricted to {', '.join(allowed_roles)}. Your current role is {request.user.role}."
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    return role_required([UserRole.ADMIN])(view_func)


def teacher_required(view_func):
    return role_required([UserRole.TEACHER, UserRole.ADMIN])(view_func)


def student_required(view_func):
    return role_required([UserRole.STUDENT])(view_func)
