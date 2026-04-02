FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY openapi.yaml .
COPY policies/ ./policies/

RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=src
EXPOSE 5000
CMD ["gunicorn", "--threads", "4", "--workers", "2", "-b", "0.0.0.0:5000", "main:app"]
