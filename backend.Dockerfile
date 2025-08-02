FROM python:3.11-slim


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app


RUN addgroup --system app && adduser --system --group app


COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt


RUN playwright install --with-deps


COPY . .


RUN chmod +x /app/entrypoint.sh


RUN chown -R app:app /app


USER app


CMD ["/app/entrypoint.sh"]