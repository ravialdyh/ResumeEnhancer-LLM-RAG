# backend.Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN addgroup --system app && adduser --system --group app

COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt


ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install-deps firefox
RUN playwright install firefox

COPY . .

RUN chmod +x /app/entrypoint.sh
RUN chown -R app:app /app

USER app

CMD ["/app/entrypoint.sh"]