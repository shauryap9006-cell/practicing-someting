# RailTwin-X v4 — Production Dockerfile
# SIH 2026 PS 26028 · Delay Intelligence Engine

FROM python:3.11-slim

LABEL maintainer="RailTwin-X SIH Team" \
      description="RailTwin-X Delay Intelligence API Server" \
      version="4.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RAILTWIN_API_HOST=0.0.0.0 \
    RAILTWIN_API_PORT=8000 \
    RAILTWIN_UVICORN_WORKERS=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create necessary directories
RUN mkdir -p artifacts data/cache data/backups

# Seed database on build (passenger mode) — for demo/CI only.
# Runtime deployments should mount an external database path and run migrations.
RUN python -m data.seed --network=passenger

# Run as an unprivileged user; the data volume must be writable by this uid.
RUN useradd --system --uid 10001 --create-home railtwin \
    && chown -R railtwin:railtwin /app
USER railtwin

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f "http://localhost:${RAILTWIN_API_PORT}/readyz" || exit 1

# Single worker by default: rate limiting, idempotency, SSE slots, the simulated
# clock and the live tracker loop are process-local and SQLite is single-writer.
# Scale horizontally with separate containers + shared cache if needed.
CMD ["sh", "-c", "python -m uvicorn api.main:app --host \"$RAILTWIN_API_HOST\" --port \"$RAILTWIN_API_PORT\" --workers \"$RAILTWIN_UVICORN_WORKERS\" --proxy-headers"]
