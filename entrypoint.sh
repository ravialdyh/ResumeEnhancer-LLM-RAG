#!/bin/sh

set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "db" -p "5432" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"; do
  sleep 2
done
echo "PostgreSQL is ready."

echo "Applying database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000