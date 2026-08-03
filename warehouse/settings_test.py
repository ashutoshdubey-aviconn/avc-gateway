"""Settings used for fast unit tests (SQLite, eager Celery)."""
import os

from .settings import *  # noqa: F401,F403

# Keep a stable secret for CI tests if not provided
SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key")
DEBUG = True

# Use in-memory SQLite to keep unit tests fast and isolated
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up password hashing for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Run Celery tasks synchronously during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use local memory email backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
"""
Module warehouse.settings_test

Flow:
"""

import importlib

# Import base settings module and copy uppercase attributes to this module's
# globals. This avoids `from .settings import *` while preserving behavior.
base_settings = importlib.import_module("warehouse.settings")
for _name in dir(base_settings):
    if _name.isupper():
        globals()[_name] = getattr(base_settings, _name)

# Testing settings override: use SQLite in-memory database to avoid requiring
# an external Postgres server during CI or local test runs.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Ensure we have a predictable secret key and debug on for tests
SECRET_KEY = "test-secret-key"
DEBUG = True

# Ensure tests in the `mqtt` package (non-Django-app tests) are discovered
# by the Django test runner during `manage.py test` runs used for CI/local
# verification. Some test modules live under `mqtt/tests` and `mqtt` is not
# a regular Django app; adding it here only for the test settings ensures
# those tests run in the in-memory test environment.
# base settings provided INSTALLED_APPS as a sequence; coerce to list when present
base_installed = globals().get("INSTALLED_APPS")
if base_installed:
    INSTALLED_APPS = list(base_installed) + ["mqtt"]
else:
    INSTALLED_APPS = ["mqtt"]
