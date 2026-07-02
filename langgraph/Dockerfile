# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools required for any compiled deps (e.g. numpy, scikit-learn)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first for layer caching
COPY pyproject.toml ./

# Install all dependencies into a prefix directory so we can copy them cleanly
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install ".[langgraph]" 2>/dev/null \
    || pip install --no-cache-dir --prefix=/install .

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser

# Copy agent source directories
COPY agents/ ./agents/
COPY tools/ ./tools/
COPY rag/ ./rag/

# Transfer ownership to non-root user
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8081

CMD ["python", "-m", "agents.graph"]
