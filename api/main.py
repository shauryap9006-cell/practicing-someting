"""RailTwin-X FastAPI Application Server.

Entrypoint launching the REST API server on uvicorn with interactive Swagger docs,
comprehensive RBAC, cryptographic audit logs, shift handovers, timetable management,
live train boards, platform consoles, block sections, and Gantt day planner.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import torch
import uvicorn

from config import settings
from data.db import get_db
from api.routes import router as v1_router
from api.auth_routes import router as auth_router
from api.audit_routes import router as audit_router
from api.notification_routes import router as notification_router
from api.timetable_routes import router as timetable_router
from api.board_routes import router as board_router
from api.platform_routes import router as platform_router
from api.block_routes import router as block_router
from api.planner_routes import router as planner_router
from api.system_routes import router as system_router
from api.safety_routes import router as safety_router
from api.workforce_routes import router as workforce_router
from api.section_routes import router as section_router
from api.admin_routes import router as admin_router
from api.handover_routes import router as handover_router
from api.infra_routes import router as infra_router
from api.ops_routes import router as ops_router
from api.commercial_routes import router as commercial_router
from api.live_routes import router as live_router
from api.passenger_routes import router as passenger_router
from engine.live_tracker import get_live_tracker
from api.middleware import IdempotencyMiddleware, ResponseCacheMiddleware, TokenBucketRateLimiter



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    print("[INFO] Starting RailTwin-X API Server...")
    # Cap torch threads to 1 to eliminate thread thrashing under concurrent uvicorn workers (F11, F33)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass

    db = get_db()
    db.init_schema()
    try:
        db.materialize_historical_baselines()
    except Exception:
        pass
    counts = db.table_counts()
    print(f"[INFO] SQLite Database initialized with {counts.get('station_events', 0):,} station events.")

    # Pipeline 07: Start background live position tracking loop
    tracker = get_live_tracker(db)
    await tracker.start()

    yield

    print("[INFO] Shutting down RailTwin-X API Server...")
    await tracker.stop()


app = FastAPI(
    title="RailTwin-X Delay Intelligence & Station Operating System API",
    description="SIH 2026 PS 26028 · Real-Time Dynamic ETA Forecasting, Safety Interlocks & Station OS Governance",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# HTTP Compression Middleware (F35)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Configure CORS for Next.js dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mutation Idempotency Middleware (F46)
app.add_middleware(IdempotencyMiddleware)

# Phase 5: 5-second TTL response cache for GET /v1/advise endpoints
app.add_middleware(ResponseCacheMiddleware)


# Phase 5: Token-bucket rate limiter (60 req/min per IP, 10-token burst)
app.add_middleware(TokenBucketRateLimiter)

# Mount Passenger Train Tracking Flow (Pipeline 08)
app.include_router(passenger_router)
app.include_router(passenger_router, prefix="/api")

# Mount Core Operational Routes
app.include_router(v1_router)
app.include_router(v1_router, prefix="/api")



@app.get("/")
def root_redirect():
    """Root redirect to interactive OpenAPI Swagger documentation."""
    return {
        "app": settings.APP_NAME,
        "version": "2.1.0",
        "description": "RailTwin-X Station Operating System & Delay Intelligence Engine",
        "docs_url": "/docs",
        "health_url": "/v1/health",
    }


def start_server():
    """Runs uvicorn development server."""
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


if __name__ == "__main__":
    start_server()
