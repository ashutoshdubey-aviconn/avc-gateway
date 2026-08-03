"""Base settings shared across environments."""

import logging
import os

from decouple import config

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = config(
    "SECRET_KEY",
    default="unsafe-dev-key-change-in-production",
)
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost,0.0.0.0",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

CORS_ORIGIN_ALLOW_ALL = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "wareApp",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "mptt",
    "django_extensions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]

ROOT_URLCONF = "warehouse.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "warehouse.wsgi.application"

AUTH_USER_MODEL = "wareApp.User"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", cast=int),
    }
}

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True
USE_L10N = True
USE_TZ = False

# Use standard Django static settings. Serve static files at `/static/`.
# Put collected static files in a top-level `staticfiles/` directory and also
# include the repository `static/` folder in `STATICFILES_DIRS` so vendor
# assets and admin files are discovered by `collectstatic`.
STATIC_URL = "/static/"
# PROJECT_ROOT is the repository root (one level above the `warehouse` package)
PROJECT_ROOT = os.path.dirname(BASE_DIR)
STATIC_ROOT = os.path.join(PROJECT_ROOT, "staticfiles")
# Additional locations the staticfiles app will traverse
STATICFILES_DIRS = [os.path.join(PROJECT_ROOT, "static")]

CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL",
    default="amqp://guest:guest@localhost:5672//",
)

CELERY_RESULT_BACKEND = None
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "gateway_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": os.path.join(LOG_DIR, "gateway.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
        "celery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": os.path.join(LOG_DIR, "celery.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
        "mqtt_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": os.path.join(LOG_DIR, "mqtt.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
        "recovery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": os.path.join(LOG_DIR, "recovery.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
        "modbus_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": os.path.join(LOG_DIR, "modbus.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
        "system_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": os.path.join(LOG_DIR, "system.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "system_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django": {
            "handlers": ["console", "system_file"],
            "level": "INFO",
            "propagate": False,
        },
        "wareApp.gateway": {
            "handlers": ["console", "gateway_file"],
            "level": "INFO",
            "propagate": False,
        },
        "wareApp.mqtt": {
            "handlers": ["console", "mqtt_file"],
            "level": "INFO",
            "propagate": False,
        },
        "wareApp.gateway.recovery": {
            "handlers": ["console", "recovery_file"],
            "level": "INFO",
            "propagate": False,
        },
        "wareApp.modbus": {
            "handlers": ["console", "modbus_file"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
