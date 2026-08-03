#!/bin/sh
set -e

echo "Waiting for database at ${DATABASE_HOST:-db}:${DATABASE_PORT:-5432}..."
host=${DATABASE_HOST:-db}
port=${DATABASE_PORT:-5432}
while ! nc -z "$host" "$port"; do
  sleep 1
done

echo "Waiting for rabbitmq at ${RABBITMQ_HOST:-rabbit}:${RABBITMQ_PORT:-5672}..."
rb_host=${RABBITMQ_HOST:-rabbit}
rb_port=${RABBITMQ_PORT:-5672}
while ! nc -z "$rb_host" "$rb_port"; do
  sleep 1
done

echo "Applying database migrations..."
python manage.py migrate --no-input

echo "Collecting static files (if configured)..."
python manage.py collectstatic --no-input || true

echo "Starting process: $@"
exec "$@"
