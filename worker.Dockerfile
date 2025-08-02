FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN addgroup --system app && adduser --system --group app

COPY worker-requirements.txt .
RUN pip install --no-cache-dir -r worker-requirements.txt

RUN mkdir -p /app/scripts

COPY scripts/download_model.py /app/scripts/

RUN python /app/scripts/download_model.py

COPY . .

RUN chown -R app:app /app

USER app

CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]