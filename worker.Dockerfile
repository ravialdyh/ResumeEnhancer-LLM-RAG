FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir celery redis
COPY . .
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]