FROM python:3.11-slim

# Create non-root user early so we can chown the workdir
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Copy and install dependencies first — layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/
COPY mock_model.py .

# Hand ownership of the workdir to the non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Container-level health check — orchestrators (ECS, k8s) use this
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
