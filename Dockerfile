# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-build
WORKDIR /build

COPY package.json package-lock.json ./
COPY packages/ ./packages/
COPY web/package.json ./web/
COPY livewall/package.json ./livewall/
RUN npm ci

COPY web/ ./web/
RUN npm run build --workspace web

# Stage 2: Python Backend Runtime
FROM python:3.11-slim AS backend

LABEL maintainer="RailTwin-X SIH Team" \
      description="RailTwin-X Full-Stack Delay Intelligence & Digital Twin System" \
      version="4.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RAILTWIN_API_HOST=0.0.0.0 \
    RAILTWIN_API_PORT=8000 \
    RAILTWIN_UVICORN_WORKERS=1

# System dependencies (curl for healthcheck, compilers for native packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source directories
COPY api/ ./api/
COPY engine/ ./engine/
COPY ml/ ./ml/
COPY safety/ ./safety/
COPY notifications/ ./notifications/
COPY collector/ ./collector/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY config.py .

# Copy built frontend assets from Stage 1
COPY --from=frontend-build /build/web/dist ./web/dist

# Create necessary runtime directories
RUN mkdir -p data/cache data/backups

# Create unprivileged application user
RUN useradd --system --uid 10001 --create-home railtwin \
    && chown -R railtwin:railtwin /app
USER railtwin

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f "http://localhost:8000/readyz" || exit 1

# Single worker: process-local state architecture (clock, tracker, SQLite single-writer)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
