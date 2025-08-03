FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt

RUN playwright install firefox --with-deps

COPY . .

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]