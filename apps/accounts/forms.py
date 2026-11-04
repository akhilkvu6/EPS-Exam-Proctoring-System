"""
Forms for authentication and account management.
Compliant with Section 7 (Username/Password authentication without paid OTP dependencies).
"""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from .models import User, UserRole, UserStatus


class LoginForm(forms.Form):
    """
    Primary institutional login form.
    Validates username, password, and institutional status.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter username",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
        label=_("Username"),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        ),
        label=_("Password"),
    )
    intended_role = forms.ChoiceField(
        choices=[("", "Any Role")] + UserRole.choices,
        required=False,
        widget=forms.HiddenInput(),
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        intended_role = cleaned_data.get("intended_role")

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError(
                    _("Invalid username or password. Please verify your credentials.")
                )

            if not user.is_active:
                raise forms.ValidationError(
                    _("This account is currently disabled. Contact institutional support.")
                )

            if user.status == UserStatus.SUSPENDED:
                raise forms.ValidationError(
                    _("This account has been administratively suspended. Contact the administrative office.")
                )

            # Check role match if user specifically targeted a role tab
            if intended_role and not user.is_superuser:
                if user.role != intended_role:
                    raise forms.ValidationError(
                        _(
                            f"Account authenticated, but you are not registered as {intended_role}. "
                            f"Your registered role is {user.get_role_display()}."
                        )
                    )

            cleaned_data["user"] = user

        return cleaned_data
