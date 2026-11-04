"""
Class-based view mixins for role authorization in EPS Phoenix.
"""

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserRole, UserStatus


class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin verifying that the user is authenticated and has an allowed role.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if request.user.status == UserStatus.PENDING_APPROVAL:
            messages.warning(
                request,
                "Your registration is currently pending institutional approval.",
            )
            return redirect("accounts:account_status")

        if request.user.status == UserStatus.SUSPENDED:
            messages.error(
                request,
                "Your account has been suspended by administration.",
            )
            return redirect("accounts:account_status")

        if not request.user.is_active:
            raise PermissionDenied("Account is disabled.")

        if self.allowed_roles and request.user.role not in self.allowed_roles:
            raise PermissionDenied("You do not possess the required role permissions.")

        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRole.ADMIN]


class TeacherRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRole.TEACHER, UserRole.ADMIN]


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRole.STUDENT]
