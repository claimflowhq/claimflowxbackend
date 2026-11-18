#!/bin/sh
set -e

HOST="${POSTGRES_HOST:-$DB_HOST}"
PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"

echo "Waiting for PostgreSQL if database host is set..."
if [ -n "$HOST" ]; then
    while ! nc -z "$HOST" "$PORT"; do
        echo "Waiting for postgres at $HOST:$PORT..."
        sleep 1
    done
    echo "PostgreSQL started at $HOST:$PORT"
fi

if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Ensuring ClaimFlow superuser..."
    python manage.py ensure_superuser || true

    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear || true
else
    echo "Skipping migrations (RUN_MIGRATIONS=$RUN_MIGRATIONS)"
fi

exec "$@"
