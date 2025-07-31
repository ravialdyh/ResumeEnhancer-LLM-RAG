# backend.Dockerfile
FROM python:3.10-slim
WORKDIR /app

# Use the correct package name here
RUN apt-get update && apt-get install -y postgresql-client

COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt

RUN playwright install

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh