"""Integration test settings that read configuration from the environment."""
import os

from ..settings.base import *  # noqa: F401,F403

SECRET_KEY = os.environ.get("SECRET_KEY", "integration-secret")
DEBUG = os.environ.get("DEBUG", "False") == "True"

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

CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL", os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
)
