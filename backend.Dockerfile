# backend.Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy only the backend-specific requirements file
COPY backend-requirements.txt .

# Install backend dependencies
RUN pip install --no-cache-dir -r backend-requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]