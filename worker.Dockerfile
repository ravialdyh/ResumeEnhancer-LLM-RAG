# worker.Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy only the worker-specific requirements file
COPY worker-requirements.txt .

# Install worker dependencies
RUN pip install --no-cache-dir -r worker-requirements.txt

COPY . .

# Run the Celery worker
CMD ["celery", "-A", "workers.celery_app:celery_app", "worker", "--loglevel=info"]