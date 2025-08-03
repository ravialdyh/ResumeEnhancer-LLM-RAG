FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


RUN mkdir -p /root/.cache/pip

COPY backend-requirements.txt .

RUN pip install --no-cache-dir -r backend-requirements.txt


RUN playwright install-deps firefox \
    && playwright install firefox


RUN mkdir -p /root/.fontconfig && chmod 755 /root/.fontconfig

COPY . .

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]