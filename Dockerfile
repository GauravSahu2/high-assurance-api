# Multi-stage build for minimal attack surface
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.in .
RUN pip install pip-tools && pip-compile requirements.in -o requirements.txt
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ src/
COPY openapi.yaml openapi.yaml
EXPOSE 8000

# Run as unprivileged user for security
RUN adduser --disabled-password --no-create-home appuser && chown -R appuser /app
USER appuser

CMD ["python", "src/main.py"]
