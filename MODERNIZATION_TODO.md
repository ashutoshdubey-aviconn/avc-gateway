# Modernization & Django 5 Upgrade TODO

This file lists prioritized modernization tasks for the repository and tracks completion.

Priority 1 — Required for Django 5 upgrade and production hardening
- [x] Replace `print()` with structured `logging` across codebase.
- [x] Add `LOGGING` config to `warehouse/settings.py`.
- [x] Add `black`, `isort`, `flake8` and pre-commit hooks; format repository.
- [x] Add unit tests for MQTT routing and handlers (tests added under `mqtt/tests`, 12 tests passed).
- [x] Replace `from ... import *` occurrences in `wareApp/admin.py` and `wareApp/views.py`.
 - [x] Finish replacing remaining `from ... import *` usages across project files.
 - [x] Audit and remove project-level `# noqa` suppressions where safe.
 - [x] Audit and remove remaining `# noqa` in less-critical files (third-party `venv/` occurrences ignored).

Notes:
- A repository-wide scan found no `from ... import *` usages in project source files. Remaining `# noqa` occurrences are limited to third-party packages in `venv/` and vendored code and are not modified.

Priority 2 — Django 5 upgrade steps
- [x] Update `requirements.txt` to target Django 5.x and pin versions (pinned to venv state).
- [x] Install updated requirements in venv and run `python manage.py check` (no system check issues).
- [x] Fix deprecations and API issues discovered (upgraded `django-mptt` to `0.18.0`).
- [ ] Run full project test-suite and address any failures (partial: `mqtt` tests run; other apps have no tests yet).

Priority 3 — Productivity, packaging & CI
- [x] Add GitHub Actions workflow to run pre-commit, flake8, and tests on PRs (CI updated).
- [x] Add Docker integration artifacts for CI: `docker/Dockerfile`, `docker/docker-compose.integration.yml` (integration runs tested with Postgres + Mosquitto).
- [ ] Wire integration tests into CI job gating (ensure heavy job runs on demand/labels).
- [ ] Add `mypy` gradually and add type hints for public functions.

Priority 4 — Observability and Reliability
- [ ] Add metrics (Prometheus client) and health endpoints.
- [ ] Replace remaining broad `except Exception:` with specific exceptions and logging.
- [ ] Add monitoring & logging aggregation config (e.g., JSON logs, stdout).

**Modernization update (2026-07-28)**

- **Branch & tag:** `feature/django-upgrade` branch created and pushed; tag `django-5.2.16` added.
- **Dependencies:** Upgraded to `Django==5.2.16` and pinned compatible packages in `requirements.txt`.
- **Formatting & tooling:** `black`, `isort`, `flake8`, and `pre-commit` added and run across the repo.
- **Logging:** `print()` usages replaced and `LOGGING` configured in `warehouse/settings.py`.
- **MQTT routing & handlers:** Centralized in `mqtt/router.py`; handlers moved into `load/`, `energy/`, and `gateway/` modules.
- **Tests:** Added `mqtt` unit tests (12 tests) and verified they pass under `warehouse.settings_test` (in-memory DB). To ensure discovery, `mqtt` was added to `INSTALLED_APPS` inside `warehouse/settings_test.py` for test runs.
- **Docker/CI:** Integration Docker artifacts added and integration runs tested locally; CI workflow updated to include tests and (optionally) integration job.

**Next recommended actions**
- Finish replacing remaining `from ... import *` usages across the project and remove remaining `# noqa` where safe.
- Add `mypy` checks for core modules (`mqtt/`, `load/`, `energy/`) and begin adding type hints to public APIs.
- Wire the mqtt unit tests into CI (either run the explicit `mqtt.tests` modules or keep the `settings_test` tweak and run `manage.py test --settings=warehouse.settings_test`).
- Add a short `docker/README.md` documenting integration test steps and port remapping guidance.

Execution notes
- Work incrementally; prefer small, reviewable commits per task (tests, typing, imports).
- Integration tests are sensitive to host ports (avoid binding standard broker/db ports on developer machines — use remapped ports in compose).

Next immediate actions
- Create a short CI change: run `./venv/bin/python manage.py test mqtt.tests --settings=warehouse.settings_test` in CI, or add mqtt to `INSTALLED_APPS` in test settings (already done).
- Start `mypy` configuration and run on `mqtt/` and `load/` modules.
