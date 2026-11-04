"""
Production settings for EPS Phoenix.
"""

from .base import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

if SECRET_KEY == "eps-phoenix-development-insecure-key-do-not-use-in-production-1234567890":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be configured with a unique, secret production value!"
    )

# Strict production security flags
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production static storage with whitenoise compression and caching
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
