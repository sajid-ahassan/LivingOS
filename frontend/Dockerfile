# LivingOps frontend: zero-build static pages plus the /api proxy.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 FRONTEND_HOST=0.0.0.0 FRONTEND_PORT=5173
WORKDIR /app
COPY . .

EXPOSE 5173
CMD ["python", "serve_frontend.py"]
