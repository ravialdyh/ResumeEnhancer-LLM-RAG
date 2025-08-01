# worker.Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY worker-requirements.txt .

RUN pip install --no-cache-dir -r worker-requirements.txt

COPY . .

# Run the Celery worker
CMD ["celery", "-A", "workers.celery_app:celery_app", "worker", "--loglevel=info"]