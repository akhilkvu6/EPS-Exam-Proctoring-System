import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from apps.accounts.decorators import active_user_required
from apps.appearance.models import (
    UserAppearancePreference,
    ThemeMode,
    InterfaceDensity,
)


@login_required
@active_user_required
def appearance_settings_view(request):
    """
    ChatGPT-inspired appearance customizer supporting light/dark/system themes,
    accent hues, density options, and contrast toggles.
    """
    user = request.user
    pref, _ = UserAppearancePreference.objects.get_or_create(user=user)

    if request.method == "POST":
        theme_mode = request.POST.get("theme_mode", ThemeMode.SYSTEM)
        accent = request.POST.get("accent_color", "#3b82f6")
        density = request.POST.get("density", InterfaceDensity.COMFORTABLE)
        high_contrast = request.POST.get("high_contrast") == "on"

        pref.theme_mode = theme_mode
        pref.accent_color = accent
        pref.density = density
        pref.high_contrast = high_contrast
        pref.save()

        messages.success(request, "Appearance preferences saved successfully.")
        response = redirect("appearance:settings")
        # Persist in cookies for non-FOUC immediate SSR
        response.set_cookie("theme_mode", theme_mode, max_age=31536000)
        response.set_cookie("accent_color", accent, max_age=31536000)
        return response

    context = {
        "pref": pref,
        "theme_modes": ThemeMode.choices,
        "densities": InterfaceDensity.choices,
    }
    return render(request, "appearance/settings.html", context)


@login_required
@active_user_required
@require_POST
def api_update_appearance(request):
    """Instant JSON endpoint for seamless client theme adjustments."""
    user = request.user
    pref, _ = UserAppearancePreference.objects.get_or_create(user=user)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body.")

    theme_mode = body.get("theme_mode")
    accent = body.get("accent_color")
    density = body.get("density")
    high_contrast = body.get("high_contrast")

    if theme_mode in dict(ThemeMode.choices):
        pref.theme_mode = theme_mode
    if accent:
        pref.accent_color = accent
    if density in dict(InterfaceDensity.choices):
        pref.density = density
    if high_contrast is not None:
        pref.high_contrast = bool(high_contrast)

    pref.save()

    response = JsonResponse({
        "status": "updated",
        "theme_mode": pref.theme_mode,
        "accent_color": pref.accent_color,
        "density": pref.density,
    })
    response.set_cookie("theme_mode", pref.theme_mode, max_age=31536000)
    response.set_cookie("accent_color", pref.accent_color, max_age=31536000)
    return response
