"""
Context processors for core application metadata.
"""

from django.conf import settings


def institution_context(request):
    """
    Exposes platform and institutional branding variables to all templates.
    """
    return {
        "INSTITUTION_NAME": getattr(settings, "INSTITUTION_NAME", "Phoenix Institute of Technology"),
        "PLATFORM_NAME": getattr(settings, "PLATFORM_NAME", "EPS Phoenix"),
        "PLATFORM_VERSION": getattr(settings, "PLATFORM_VERSION", "3.0.0"),
    }
