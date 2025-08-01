# backend.Dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client

COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt

RUN playwright install

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh