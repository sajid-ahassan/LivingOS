# LivingOps backend. Build from the repository root:
#   docker build -f backend/Dockerfile .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Seed policies, demo AI cache and the trained anomaly model live next to
# the backend, as in the repository (config resolves PROJECT_ROOT=/app).
COPY data/seed /app/data/seed
COPY data/demo_cache /app/data/demo_cache
COPY models /app/models
COPY backend /app/backend

EXPOSE 8000
CMD ["sh", "-c", "python -m app.scripts.bootstrap && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
