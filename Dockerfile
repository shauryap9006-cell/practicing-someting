# RailTwin-X v4 — Production Dockerfile
# SIH 2026 PS 26028 · Delay Intelligence Engine

FROM python:3.11-slim

LABEL maintainer="RailTwin-X SIH Team" \
      description="RailTwin-X Delay Intelligence API Server" \
      version="4.0.0"

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
RUN mkdir -p artifacts data/cache

# Seed database on build (passenger mode) — for demo/CI
# In production, override with docker-compose volume + nightly pipeline
RUN python -m data.seed --network=passenger

# Train models (if not pre-built) — comment out for fast image builds
# RUN python -m ml.train && python -m ml.model_seq && python -m ml.ensemble && python -m ml.evaluate

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Start the API server
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
