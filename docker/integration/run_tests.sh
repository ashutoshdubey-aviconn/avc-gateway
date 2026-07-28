#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for Postgres..."
for i in {1..30}; do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
    echo "Postgres is ready"
    break
  fi
  sleep 1
done

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-warehouse.settings_integration}

echo "Running Django tests (integration)..."
python manage.py migrate --noinput
python manage.py test --verbosity=2
