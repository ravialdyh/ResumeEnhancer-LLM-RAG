#!/bin/sh

set -e

echo "Waiting for PostgreSQL to be ready..."

while ! pg_isready -d "$DATABASE_URL" -q; do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Applying database migrations..."
alembic upgrade head

# Start the main application
echo "Starting FastAPI server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000