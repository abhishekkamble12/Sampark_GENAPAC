# ==============================================================================
# Sampark AI Platform — Unified Multi-Stage Dockerfile
#
# Builds and runs the entire Sampark AI application (React frontend +
# FastAPI backend + LangGraph agents + RAG pipeline) in a single container.
#
# Architecture:
#   Stage 1 (frontend-builder)  — Builds the React/Vite SPA
#   Stage 2 (python-builder)    — Installs all Python dependencies
#   Stage 3 (runtime)           — Runs nginx (frontend) + uvicorn (backend)
#
# No Google Cloud billing required. Uses only free/open-source components:
#   - SQLite (database)
#   - DuckDB (analytics)
#   - FAISS (vector search)
#   - Gemini API (AI — free tier via AI Studio)
# ==============================================================================

# ─── Stage 1: Frontend Builder ───────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app/frontend

# Copy dependency manifests first for optimal layer caching
COPY frontend/package.json frontend/package-lock.json ./

# Install exact dependencies defined in lockfile
RUN npm ci

# Copy remaining frontend source files
COPY frontend/ ./

# Build Vite/React app — output lands in /app/frontend/dist
# VITE_API_BASE_URL is baked in at build time (defaults to http://localhost:8000)
RUN npm run build


# ─── Stage 2: Python Dependency Builder ──────────────────────────────────────
FROM python:3.12-slim AS python-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools required for compiled dependencies (numpy, faiss-cpu, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first for layer caching
COPY pyproject.toml ./

# Install all dependencies into a prefix directory so we can copy them cleanly
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install ".[dev]"


# ─── Stage 3: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_MODE=local \
    CORS_ALLOWED_ORIGINS=*

WORKDIR /app

# Install nginx for serving the built frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /etc/nginx/conf.d/default.conf

# Copy Python packages from builder stage
COPY --from=python-builder /install /usr/local

# Copy backend source code
COPY backend/ ./backend/

# Copy agents
COPY agents/ ./agents/

# Copy tools
COPY tools/ ./tools/

# Copy RAG pipeline
COPY rag/ ./rag/

# Copy functions
COPY functions/ ./functions/

# Copy pyproject.toml (for package metadata)
COPY pyproject.toml ./

# Copy built frontend assets from the frontend builder stage
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# Copy nginx configuration for SPA serving
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Create data directory for SQLite / DuckDB / FAISS storage
RUN mkdir -p /app/data

# Copy entrypoint script (separate file for clarity and maintainability)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser \
    && chown -R appuser:appgroup /app /usr/share/nginx/html /var/log/nginx /var/lib/nginx

# Switch to non-root user
USER appuser

# Expose ports:
#   8000 — FastAPI backend (serves JSON API + SSE streams)
#   8080 — nginx frontend (serves the React SPA, proxied or direct)
EXPOSE 8000 8080

# Health check — verifies the backend is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
