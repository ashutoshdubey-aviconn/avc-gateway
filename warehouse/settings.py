"""Compatibility loader for environment-specific settings.

This module keeps the import path `warehouse.settings` working while allowing
selection of an environment-specific settings module via the `DJANGO_ENV`
environment variable. Valid values: `production`, `development`, `test`,
`integration`. The default is `production`.
"""

import os

_env = os.environ.get("DJANGO_ENV", "production").strip().lower()

if _env == "test":
    from .settings.test import *  # noqa: F401,F403
elif _env == "integration":
    from .settings.integration import *  # noqa: F401,F403
elif _env == "development":
    from .settings.development import *  # noqa: F401,F403
else:
    from .settings.production import *  # noqa: F401,F403
