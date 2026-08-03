"""Test settings (lightweight) for unit tests."""
import os

from ..settings.base import *  # noqa: F401,F403

# Use in-memory SQLite for fast tests
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Predictable secret for tests
SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key")
DEBUG = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
