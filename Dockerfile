FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps needed for common Python packages and `nc` for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# install python deps
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# copy project
COPY . /app/

# entrypoint will wait for services and run migrations before starting
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DJANGO_SETTINGS_MODULE=warehouse.settings

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

# For interactive development use the Django dev server by default. In
# production or CI use the `gunicorn` command via docker-compose override or
# by passing a different command to `docker run` / `docker-compose`.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
