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
# BOOTSTRAP_ON_START=true (docker compose) prepares an empty database; it
# re-seeds the demo company, so hosted deployments (Render, which restarts
# sleeping services on the next request) set it to false. PORT comes from
# the host when it assigns one.
ENV BOOTSTRAP_ON_START=true
CMD ["sh", "-c", "if [ \"$BOOTSTRAP_ON_START\" = \"true\" ]; then python -m app.scripts.bootstrap; fi && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
