#!/bin/sh

until psql -h "db" -U "user" -d "resume_db" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"

# Run database migrations
alembic upgrade head

# Start the FastAPI application
exec uvicorn api.main:app --host 0.0.0.0 --port 8000