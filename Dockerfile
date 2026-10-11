FROM node:22-bookworm AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIPELINE_MODE=real \
    UPLOAD_DIR=/app/data/uploads

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg git libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-real.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-real.txt

COPY backend/ /app/backend/
WORKDIR /app/backend
RUN mkdir -p /app/data/uploads

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM nginx:1.27-alpine AS frontend-runtime

COPY --from=frontend-build /app/frontend/dist/frontend/browser /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
