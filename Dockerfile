# ==============================================================================
# Sampark AI Platform — Unified Multi-Stage Dockerfile
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1 — Frontend Builder
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app/frontend

COPY frontend/package*.json ./

RUN npm ci

COPY frontend/ .

RUN npm run build


# ------------------------------------------------------------------------------
# Stage 2 — Python Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS python-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy metadata FIRST
COPY pyproject.toml ./
COPY README.md ./

# Copy Python packages required by Hatchling
COPY backend ./backend
COPY agents ./agents
COPY rag ./rag
COPY tools ./tools
COPY functions ./functions

# Install package + dependencies
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install ".[dev]"


# ------------------------------------------------------------------------------
# Stage 3 — Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_MODE=local \
    CORS_ALLOWED_ORIGINS=*

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/conf.d/default.conf

# Python packages
COPY --from=python-builder /install /usr/local

# Backend source
COPY backend ./backend
COPY agents ./agents
COPY rag ./rag
COPY tools ./tools
COPY functions ./functions

# Metadata
COPY pyproject.toml ./
COPY README.md ./

# Frontend
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /app/data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m appuser && \
    chown -R appuser:appgroup \
        /app \
        /usr/share/nginx/html \
        /var/log/nginx \
        /var/lib/nginx \
        /var/cache/nginx

USER appuser

EXPOSE 8000 8080

HEALTHCHECK --interval=30s \
             --timeout=10s \
             --start-period=20s \
             --retries=3 \
CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]