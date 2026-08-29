"""RailTwin-X API Middleware — Phase 5 (API Hardening).

Provides:
1. ResponseCacheMiddleware  — 5-second in-memory TTL cache for GET /v1/advise
2. TokenBucketRateLimiter  — 60 req/min per IP (configurable) using token-bucket algorithm
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Dict, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# ---------------------------------------------------------------------------
# 1. In-memory TTL Response Cache
# ---------------------------------------------------------------------------

class _CacheEntry:
    __slots__ = ("body", "status_code", "headers", "expires_at")

    def __init__(self, body: bytes, status_code: int, headers: dict, ttl_sec: float):
        self.body = body
        self.status_code = status_code
        self.headers = headers
        self.expires_at = time.monotonic() + ttl_sec


_CACHE: Dict[str, _CacheEntry] = {}
_CACHE_LOCK = asyncio.Lock()

# Endpoints to cache (prefix match on path)
_CACHE_PREFIXES = ("/v1/advise", "/api/advise")
_CACHE_TTL_SEC = 5.0


def _cache_key(request: Request) -> str:
    """Deterministic key from method + path + sorted query string."""
    raw = f"{request.method}:{request.url.path}?{request.url.query}"
    return hashlib.md5(raw.encode()).hexdigest()


def _should_cache(request: Request) -> bool:
    return request.method == "GET" and any(
        request.url.path.startswith(p) for p in _CACHE_PREFIXES
    )


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """5-second TTL in-memory cache for GET /v1/advise endpoints."""

    async def dispatch(self, request: Request, call_next):
        if not _should_cache(request):
            return await call_next(request)

        key = _cache_key(request)

        async with _CACHE_LOCK:
            entry = _CACHE.get(key)
            if entry and time.monotonic() < entry.expires_at:
                # Cache hit
                return Response(
                    content=entry.body,
                    status_code=entry.status_code,
                    headers={**dict(entry.headers), "X-Cache": "HIT"},
                    media_type="application/json",
                )

        # Cache miss — call the real handler
        response = await call_next(request)

        # Only cache 200 OK responses
        if response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            async with _CACHE_LOCK:
                _CACHE[key] = _CacheEntry(
                    body=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    ttl_sec=_CACHE_TTL_SEC,
                )
            return Response(
                content=body,
                status_code=response.status_code,
                headers={**dict(response.headers), "X-Cache": "MISS"},
                media_type="application/json",
            )

        return response


# ---------------------------------------------------------------------------
# 2. Token-Bucket Rate Limiter
# ---------------------------------------------------------------------------

_RATE_LIMIT_RPM = 60          # requests per minute per IP
_RATE_LIMIT_BURST = 10        # max burst above steady rate
_BUCKET_REFILL_RATE = _RATE_LIMIT_RPM / 60.0  # tokens/sec

_BUCKETS: Dict[str, Tuple[float, float]] = {}   # ip -> (tokens, last_refill_ts)
_BUCKET_LOCK = asyncio.Lock()


def _get_client_ip(request: Request) -> str:
    """Extracts real client IP, respecting X-Forwarded-For header for reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class TokenBucketRateLimiter(BaseHTTPMiddleware):
    """60 req/min per IP token-bucket rate limiter. Returns 429 on exhaustion.

    Bypassed when:
    - client IP is 'unknown' or 'testclient' (FastAPI TestClient, CI environments)
    - RAILTWIN_TESTING=1 env variable is set
    """

    async def dispatch(self, request: Request, call_next):
        import os
        # Skip rate limiting for health checks, docs, and test environments
        if request.url.path in ("/v1/health", "/docs", "/redoc", "/openapi.json", "/"):
            return await call_next(request)

        ip = _get_client_ip(request)

        # Bypass for test clients (no real IP) and when testing flag is set
        if ip in ("unknown", "testclient") or os.environ.get("RAILTWIN_TESTING", "0") == "1":
            return await call_next(request)

        now = time.monotonic()

        async with _BUCKET_LOCK:
            tokens, last_refill = _BUCKETS.get(ip, (float(_RATE_LIMIT_BURST), now))
            # Refill tokens based on elapsed time
            elapsed = now - last_refill
            tokens = min(float(_RATE_LIMIT_BURST), tokens + elapsed * _BUCKET_REFILL_RATE)

            if tokens < 1.0:
                _BUCKETS[ip] = (tokens, now)
                retry_after = int((1.0 - tokens) / _BUCKET_REFILL_RATE) + 1
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded: {_RATE_LIMIT_RPM} req/min per IP.",
                            "retryable": True,
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # Consume one token
            tokens -= 1.0
            _BUCKETS[ip] = (tokens, now)

        return await call_next(request)


# ---------------------------------------------------------------------------
# 3. Mutation Idempotency Middleware (F46)
# ---------------------------------------------------------------------------

_IDEMPOTENCY_CACHE: Dict[str, Tuple[int, bytes, dict, float]] = {}  # key -> (status, body, headers, timestamp)
_IDEMPOTENCY_LOCK = asyncio.Lock()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Guarantees mutation idempotency on POST/PUT/DELETE when Idempotency-Key header is supplied."""

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        async with _IDEMPOTENCY_LOCK:
            cached = _IDEMPOTENCY_CACHE.get(idempotency_key)
            if cached:
                status_code, body, headers, _ = cached
                return Response(
                    content=body,
                    status_code=status_code,
                    headers={**headers, "X-Idempotent-Replay": "true"},
                    media_type="application/json",
                )

        response = await call_next(request)

        if 200 <= response.status_code < 300:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            async with _IDEMPOTENCY_LOCK:
                _IDEMPOTENCY_CACHE[idempotency_key] = (
                    response.status_code,
                    body,
                    dict(response.headers),
                    time.time(),
                )

            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )

        return response

