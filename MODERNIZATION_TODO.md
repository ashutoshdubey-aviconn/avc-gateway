# Modernization & Django 5 Upgrade TODO

This file lists prioritized modernization tasks for the repository and tracks completion.

Priority 1 — Required for Django 5 upgrade and production hardening
- [x] Replace `print()` with structured `logging` across codebase. (done)
- [x] Add `LOGGING` config to `warehouse/settings.py`. (done)
- [x] Add `black`, `isort`, `flake8` and pre-commit hooks; format repository. (done)
- [ ] Replace all `from ... import *` occurrences with explicit imports (start with `wareApp`).
- [ ] Audit and remove `# noqa` suppressions where possible.
- [ ] Add unit tests for MQTT routing and handlers.
 - [x] Replace all `from ... import *` occurrences with explicit imports (start with `wareApp`).
 - [x] Audit and remove `# noqa` suppressions where possible (project-level).
 - [x] Add unit tests for MQTT routing and handlers.
 - [x] Replace all `from ... import *` occurrences with explicit imports in `wareApp/admin.py` and `wareApp/views.py`.
 - [ ] Audit and remove `# noqa` suppressions where possible.
 - [ ] Add unit tests for MQTT routing and handlers.

Priority 2 — Django 5 upgrade steps
- [ ] Update `requirements.txt` to target Django 5.x (use a test branch and pin a version).
- [ ] Run `pip install -r requirements.txt` in a disposable environment and run `python manage.py check`.
- [ ] Fix deprecations and API changes: settings changes, URL settings, middleware, removed APIs.
- [ ] Run test-suite and address failures.
 - [x] Update `requirements.txt` to target Django 5.x and pin installed versions (pinned to venv state).
 - [x] Run `pip install -r requirements.txt` in the venv and run `python manage.py check` (no system check issues).
 - [x] Fix deprecations and API issues discovered (upgraded `django-mptt` to 0.18.0 to resolve `index_together` removal).
 - [ ] Run test-suite and address failures (tests run: 0 discovered).

Priority 3 — Productivity, packaging & CI
- [ ] Add GitHub Actions workflow to run pre-commit, flake8, and tests on PRs.
 - [x] Add GitHub Actions workflow to run pre-commit, flake8, and tests on PRs.
- [ ] Add `Dockerfile` and `docker-compose.yml` for integration testing (Postgres, RabbitMQ/Redis, Mosquitto).
- [ ] Add `mypy` gradually and add type hints for public functions.

Priority 4 — Observability and Reliability
- [ ] Add metrics (Prometheus client) and health endpoints.
- [ ] Replace remaining broad `except Exception:` with specific exceptions and logging.
- [ ] Add monitoring & logging aggregation config (e.g., JSON logs, stdout). 

**Modernization update (2026-07-28)**

- **Branch & tag:** Created branch `feature/django-upgrade` and pushed updates to remote; added annotated tag `django-5.2.16` and pushed it to origin.
- **Dependencies:** Upgraded Django to `5.2.16` and upgraded/pinned compatible dependencies. Updated `requirements.txt` with pinned versions from the venv.
- **Formatting & tooling:** Added `black`, `isort`, `flake8`, and `pre-commit` hooks; ran formatting and import fixes across the repo.
- **Logging:** Replaced `print()` calls with structured `logging` across MQTT, `gateway`, `load`, `energy`, and `wareApp` modules; added `LOGGING` config in `warehouse/settings.py`.
- **MQTT routing:** Centralized MQTT routing in `mqtt/router.py` and moved handler logic into domain modules under `load/`, `energy/`, and `gateway/`.
- **Django compatibility fixes:** Resolved `django-mptt` compatibility by upgrading to `0.18.0`; `manage.py check` reports no issues.
- **Tests:** Ran `./venv/bin/python manage.py test` — no tests discovered (0). Add unit tests next.
- **Outstanding high-priority items:** Add unit tests for MQTT handlers, audit/remove `# noqa`, complete replacement of any remaining `import *`, and add CI.

Next recommended actions:
- Add a minimal GitHub Actions workflow to run pre-commit and `manage.py check` on PRs.
- Add unit tests for MQTT routing and critical handlers (start with `load/current.py`, `energy/meter.py`, and `mqtt/router.py`).
- Convert or restore provisioning scripts as management commands if needed, and exclude them from strict linting if they remain scripts.
- Run `./venv/bin/python manage.py test` after adding tests and fix any failures.


Execution notes
- Work incrementally: create a feature branch for Django 5 upgrade and run checks in CI.
- Back up the repository (tags) before making large dependency upgrades.

Next immediate actions (this run)
- Create this TODO file (done)
- Replace star-imports in `wareApp/admin.py` and `wareApp/views.py` (in progress)
