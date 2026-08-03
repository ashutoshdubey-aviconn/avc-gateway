"""Settings for integration tests using Postgres/RabbitMQ/Mosquitto provided by CI."""
import os

from .settings import *  # noqa: F401,F403

SECRET_KEY = os.environ.get("SECRET_KEY", "integration-secret")
DEBUG = os.environ.get("DEBUG", "False") == "True"

# Configure database from environment (CI provides these)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "warehouse"),
        "USER": os.environ.get("DB_USER", "aviconn"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "whpass"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Prefer an explicit broker url if provided by CI
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL", os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
)
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
