FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

WORKDIR /app

ENTRYPOINT ["/bin/sh", "-c", "python manage.py test mqtt.tests.test_handlers_unit mqtt.tests.test_router mqtt.tests.test_router_handlers mqtt.tests.test_router_handlers_expanded --settings=warehouse.settings_integration -v 2"]
