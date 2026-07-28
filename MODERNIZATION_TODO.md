# Modernization & Django 5 Upgrade TODO

This file lists prioritized modernization tasks for the repository and tracks completion.

Priority 1 — Required for Django 5 upgrade and production hardening
- [x] Replace `print()` with structured `logging` across codebase. (done)
- [x] Add `LOGGING` config to `warehouse/settings.py`. (done)
- [x] Add `black`, `isort`, `flake8` and pre-commit hooks; format repository. (done)
- [ ] Replace all `from ... import *` occurrences with explicit imports (start with `wareApp`).
- [ ] Audit and remove `# noqa` suppressions where possible.
- [ ] Add unit tests for MQTT routing and handlers.

Priority 2 — Django 5 upgrade steps
- [ ] Update `requirements.txt` to target Django 5.x (use a test branch and pin a version).
- [ ] Run `pip install -r requirements.txt` in a disposable environment and run `python manage.py check`.
- [ ] Fix deprecations and API changes: settings changes, URL settings, middleware, removed APIs.
- [ ] Run test-suite and address failures.

Priority 3 — Productivity, packaging & CI
- [ ] Add GitHub Actions workflow to run pre-commit, flake8, and tests on PRs.
- [ ] Add `Dockerfile` and `docker-compose.yml` for integration testing (Postgres, RabbitMQ/Redis, Mosquitto).
- [ ] Add `mypy` gradually and add type hints for public functions.

Priority 4 — Observability and Reliability
- [ ] Add metrics (Prometheus client) and health endpoints.
- [ ] Replace remaining broad `except Exception:` with specific exceptions and logging.
- [ ] Add monitoring & logging aggregation config (e.g., JSON logs, stdout). 

Execution notes
- Work incrementally: create a feature branch for Django 5 upgrade and run checks in CI.
- Back up the repository (tags) before making large dependency upgrades.

Next immediate actions (this run)
- Create this TODO file (done)
- Replace star-imports in `wareApp/admin.py` and `wareApp/views.py` (in progress)
