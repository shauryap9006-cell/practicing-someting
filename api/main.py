"""RailTwin-X FastAPI Application Server.

Entrypoint launching the REST API server on uvicorn with interactive Swagger docs,
comprehensive RBAC, cryptographic audit logs, shift handovers, timetable management,
live train boards, platform consoles, block sections, and Gantt day planner.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import re
import sys
from uuid import uuid4

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import torch
import uvicorn

from config import settings
from data.db import get_db
from api.routes import get_health, router as v1_router
from api.auth_routes import router as auth_router
from api.access_routes import router as access_router
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
from api.live_events_routes import router as live_events_router
from api.demo_routes import router as demo_router
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
    db.materialize_historical_baselines()
    counts = db.table_counts()
    print(f"[INFO] SQLite Database initialized with {counts.get('station_events', 0):,} station events.")

    # Initialize SimulatedClock as global clock (F02, F28)
    from engine.sim_clock import get_sim_clock
    from engine.clocks import set_global_clock
    sim_clock = get_sim_clock(db)
    set_global_clock(sim_clock)

    # Pipeline 07: Start background live position tracking loop
    tracker = get_live_tracker(db)
    await tracker.start()

    yield

    print("[INFO] Shutting down RailTwin-X API Server...")
    await tracker.stop()


class RequestContextMiddleware:
    """Adds a bounded correlation ID to every request and response."""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        supplied = request.headers.get("x-request-id", "").strip()
        request_id = supplied if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", supplied) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)

    def __init__(self, app):
        self.app = app


async def security_headers(request: Request, call_next):
    """Apply browser hardening headers to every API response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    if settings.ENV.strip().lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


def _error_payload(detail, status_code: int, request_id: str) -> dict:
    """Normalizes framework and application errors without leaking internals."""
    if isinstance(detail, dict):
        code = str(detail.get("code", f"HTTP_{status_code}"))
        message = str(detail.get("message", "Request failed"))
        retryable = bool(detail.get("retryable", status_code >= 500))
        safe_detail = {
            key: detail[key]
            for key in ("code", "message", "retryable", "issues", "status")
            if key in detail
        }
    else:
        code = f"HTTP_{status_code}"
        message = str(detail or "Request failed")
        retryable = status_code >= 500 or status_code == 429
        safe_detail = message
    return {
        "detail": safe_detail,
        "error": {"code": code, "message": message, "retryable": retryable},
        "request_id": request_id,
    }


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=_error_payload(exc.detail, exc.status_code, getattr(request.state, "request_id", "")),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "retryable": False,
                "fields": exc.errors(),
            },
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_error_payload("Internal server error", 500, getattr(request.state, "request_id", "")),
    )


app = FastAPI(
    title="RailTwin-X Delay Intelligence & Station Operating System API",
    description="SIH 2026 PS 26028 · Real-Time Dynamic ETA Forecasting, Safety Interlocks & Station OS Governance",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None if settings.ENV.strip().lower() == "production" else "/docs",
    redoc_url=None if settings.ENV.strip().lower() == "production" else "/redoc",
)

app.middleware("http")(security_headers)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# HTTP Compression Middleware (F35)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Configure CORS for Next.js dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)


# Mutation Idempotency Middleware (F46)
app.add_middleware(IdempotencyMiddleware)

# Phase 5: 5-second TTL response cache for GET /v1/advise endpoints
app.add_middleware(ResponseCacheMiddleware)


# Phase 5: Token-bucket rate limiter (60 req/min per IP, 10-token burst)
app.add_middleware(TokenBucketRateLimiter)

# Correlate browser, API, database, and model logs.
app.add_middleware(RequestContextMiddleware)

# Mount every implemented router from one explicit manifest. Prefixes are kept
# here because several legacy router modules intentionally have no prefix.
ROUTER_MANIFEST = [
    (auth_router, None),
    (access_router, None),
    (audit_router, None),
    (notification_router, None),
    (timetable_router, None),
    (board_router, None),
    (platform_router, None),
    (block_router, None),
    (planner_router, None),
    (system_router, None),
    (safety_router, None),
    (workforce_router, None),
    (section_router, "/api/section"),
    (section_router, "/api/coordination"),
    (admin_router, None),
    (handover_router, None),
    (infra_router, "/api/infrastructure"),
    (infra_router, "/api/infra"),
    (ops_router, None),
    (commercial_router, None),
    (live_router, None),
    (live_events_router, None),
    (demo_router, None),
]

for route_router, route_prefix in ROUTER_MANIFEST:
    if route_prefix:
        app.include_router(route_router, prefix=route_prefix)
    else:
        app.include_router(route_router)

# Mount Passenger Train Tracking Flow (Pipeline 08), including the legacy
# /api/v1 alias used by older clients.
app.include_router(passenger_router)
app.include_router(passenger_router, prefix="/api")

# Mount core /v1 routes and retain the legacy /api/v1 alias.
app.include_router(v1_router)
app.include_router(v1_router, prefix="/api")


@app.get("/healthz", include_in_schema=False)
def liveness_probe():
    """Cheap process liveness probe that does not depend on application state."""
    return {"status": "alive"}


@app.get("/readyz", include_in_schema=False)
def readiness_probe():
    """Readiness probe backed by the same dependency/model checks as /v1/health."""
    return get_health()



@app.get("/")
def root_redirect():
    """Root redirect to interactive OpenAPI Swagger documentation."""
    docs_url = None if settings.ENV.strip().lower() == "production" else "/docs"
    return {
        "app": settings.APP_NAME,
        "version": "3.0.0",
        "description": "RailTwin-X Station Operating System & Delay Intelligence Engine",
        "docs_url": docs_url,
        "health_url": "/v1/health",
    }


def start_server():
    """Runs uvicorn development server."""
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENV.strip().lower() != "production",
    )


if __name__ == "__main__":
    start_server()
