"""
Development settings for EPS Phoenix.
"""

from .base import *  # noqa: F403

DEBUG = True

# In development, use standard static files storage without manifest hashing requirements
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Output emails to console during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Internal IPs for debug toolbar or local inspection
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]
