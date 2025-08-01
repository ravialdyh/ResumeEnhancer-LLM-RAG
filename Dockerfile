FROM python:3.11-slim

WORKDIR /app

COPY frontend-requirements.txt .

RUN pip install --no-cache-dir -r frontend-requirements.txt

RUN playwright install

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]