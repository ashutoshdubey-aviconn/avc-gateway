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
