# Dockerfile (for Streamlit Frontend)
FROM python:3.10-slim

WORKDIR /app

# Copy only the frontend-specific requirements file
COPY frontend-requirements.txt .

# Install frontend dependencies
RUN pip install --no-cache-dir -r frontend-requirements.txt

# Install Playwright browsers
RUN playwright install

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]