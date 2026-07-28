from .settings import *  # noqa: F401,F403

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
