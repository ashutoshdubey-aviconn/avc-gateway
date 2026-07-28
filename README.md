# WH Project (Warehouse Gateway)

Overview
--------
This repository contains the backend gateway services for warehouse energy monitoring and control. The system ingests MQTT messages from edge Home Gateways and meters, processes them locally (calculations, aggregation, DB persistence), and republishes status/telemetry to cloud topics as needed.

Key components
--------------
- `warehouse/` — Django project configuration and Celery integration.
- `wareApp/` — Main Django app: models, views, serializers, admin and helpers.
- `mqtt/` — MQTT clients and router; `client1.py` and `client2.py` run paho-mqtt clients; `router.py` dispatches messages to handlers.
- `gateway/` — Gateway-specific handlers (autossh, recovery, etc.).
- `load/` and `energy/` — Domain handlers for load/runtime/wattage/current/voltage/power_factor and energy calculations.
- `constants/` and `utils/` — Topic/hardware constants and small utility helpers for payloads and DB updates.

Message flow
------------
1. MQTT clients (`mqtt/client1.py`, `mqtt/client2.py`) subscribe to broker topics (e.g. `/asem/aviconn/#`, `/Acclivate/iOmniControl/#`).
2. Incoming messages are normalized and parsed by `mqtt/topic_parser.py`.
3. `mqtt/router.py` routes messages to domain handlers in `load/`, `energy/`, and `gateway/`.
4. Handlers compute, update DB models (`wareApp.models`) and publish state messages via `paho-mqtt` as needed.
5. Celery handles asynchronous/background tasks where required (`warehouse/celery.py`).

Development setup
-----------------
Prerequisites:
- Python 3.10 (project venv configured in `venv/`)
- PostgreSQL (or configure `DATABASES` to use sqlite for local quick tests)

Install and activate venv (example):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Environment
- Copy `.env.example` or set environment variables used by `python-decouple` (`SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `CELERY_BROKER_URL`).

Run migrations and start services
```bash
python manage.py migrate
python manage.py createsuperuser
# Start MQTT clients (runs forever)
python -c "from mqtt.client1 import start_client; start_client()" &
python -c "from mqtt.client2 import start_client; start_client()" &
# Start celery worker
celery -A warehouse worker -l info
# Start Django dev server
python manage.py runserver 0.0.0.0:8000
```

Linting & formatting
--------------------
- This repo uses `black`, `isort`, and `flake8`. A `.pre-commit-config.yaml` is included; install hooks and run on every commit.

Enable pre-commit hooks (once):
```bash
pip install -r requirements.txt
./venv/bin/pre-commit install
./venv/bin/pre-commit run --all-files
```

Testing
-------
- Add unit tests under `wareApp/tests.py` or `tests/` for handlers and serializers.
- Run tests via `python manage.py test`.

Production notes
----------------
- Convert provisioning scripts into Django management commands (recommended) or deliberately keep them as CLI tools and exclude from automated hooks — they currently print to stdout and are interactive.
- Add Dockerfiles and a compose setup for local integration testing (Postgres, RabbitMQ/Redis, MQTT broker like Mosquitto).
- Add GitHub Actions to run `pre-commit` on PRs and a staging deploy pipeline.
- Replace quick `# noqa` suppressions with explicit import refactors where possible.

Security & operations
---------------------
- Keep `SECRET_KEY` and DB credentials out of the repo (use environment variables / secrets manager).
- Use structured logging (the project has been migrated from `print()` to `logging`). Configure centralized logging in production.

TODO (high priority)
- Replace `from ... import *` in remaining modules with explicit imports.
- Convert interactive provisioning scripts into `manage.py` commands.
- Add unit and integration tests for MQTT routing + handlers.
- Add CI (GitHub Actions) to enforce linting and tests.

Contact / Maintainers
---------------------
For questions about design or deployment, contact the repository owner or check the `README` in the infra repo.

License
-------
Add your project license here.

----
Generated/updated on 2026-07-28 by development tooling.
# avc-gateway
