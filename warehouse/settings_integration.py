"""Integration settings: derive from main settings and override DB for CI/docker-compose."""

import os

from . import settings as base_settings

# Import all uppercase settings from base
for name, value in base_settings.__dict__.items():
    if name.isupper():
        globals()[name] = value

# Database configuration sourced from environment (set by CI/services)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "warehouse_integration"),
        "USER": os.environ.get("DB_USER", "warehouse"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "warehouse"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": int(os.environ.get("DB_PORT", 5432)),
    }
}

# Broker override for integration if needed
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", base_settings.CELERY_BROKER_URL)
