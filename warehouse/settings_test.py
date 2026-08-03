"""Settings used for fast unit tests (SQLite, eager Celery)."""

import os

# Import base/production settings and then override selected values for tests.
from .settings import *  # noqa: F401,F403

# Predictable secret for tests when not provided by the environment.
SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key")
DEBUG = True

# Use in-memory SQLite to keep unit tests fast and isolated.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Speed up password hashing for tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Run Celery tasks synchronously during tests.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use local memory email backend for tests.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
