FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

COPY . .

# Install system dependencies that some Python packages might need (good practice for stability)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]