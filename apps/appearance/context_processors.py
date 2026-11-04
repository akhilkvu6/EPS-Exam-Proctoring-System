def appearance_context(request):
    """
    Injects user-customized appearance tokens into all rendered HTML documents,
    preventing theme flash and synchronizing design system CSS variables.
    """
    pref = None
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        pref = getattr(user, "appearance_preference", None)

    if pref:
        theme_mode = pref.theme_mode.lower()
        accent = pref.accent_color
        density = pref.density.lower()
        contrast = pref.high_contrast
    else:
        theme_mode = request.COOKIES.get("theme_mode", "system").lower()
        accent = request.COOKIES.get("accent_color", "#3b82f6")
        density = request.COOKIES.get("density", "comfortable").lower()
        contrast = request.COOKIES.get("high_contrast", "false") == "true"

    return {
        "user_theme_mode": theme_mode,
        "user_accent_color": accent,
        "user_density": density,
        "user_high_contrast": contrast,
    }
