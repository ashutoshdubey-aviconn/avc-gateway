"""Settings package loader.

Selects an environment-specific settings module based on the `DJANGO_ENV`
environment variable. Valid values: `production`, `development`, `test`,
`integration`. The default is `production`.
"""

import os

_env = os.environ.get("DJANGO_ENV", "production").strip().lower()

if _env == "test":
    from .test import *  # noqa: F401,F403
elif _env == "integration":
    from .integration import *  # noqa: F401,F403
elif _env == "development":
    from .development import *  # noqa: F401,F403
else:
    from .production import *  # noqa: F401,F403
