"""RailTwin-X API Middleware — Phase 5 (API Hardening).

Provides:
1. ResponseCacheMiddleware  - short in-memory TTL cache for GET /v1/advise
2. TokenBucketRateLimiter  - configurable req/min per IP via settings.RATE_LIMIT_RPM
3. IdempotencyMiddleware   - replay-safe mutations keyed by Idempotency-Key

All tunables come from ``config.settings`` (env-overridable with the RAILTWIN_ prefix).
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from typing import Dict, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import settings


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
_CACHE_MAX_ENTRIES = 2048

# Endpoints to cache (prefix match on path)
_CACHE_PREFIXES = ("/v1/advise", "/api/advise")


def _cache_key(request: Request) -> str:
    """Deterministic key scoped to method, query, and authenticated principal."""
    auth = request.headers.get("Authorization", "")
    principal = hashlib.sha256(auth.encode("utf-8")).hexdigest() if auth else "anonymous"
    raw = f"{principal}:{request.method}:{request.url.path}?{request.url.query}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _should_cache(request: Request) -> bool:
    return request.method == "GET" and any(
        request.url.path.startswith(p) for p in _CACHE_PREFIXES
    )


def _prune_cache(now: float) -> None:
    """Drops expired entries; must be called with _CACHE_LOCK held."""
    expired = [key for key, entry in _CACHE.items() if entry.expires_at <= now]
    for key in expired:
        _CACHE.pop(key, None)
    if len(_CACHE) > _CACHE_MAX_ENTRIES:
        # Evict oldest-expiring entries first to keep memory bounded.
        for key, _ in sorted(_CACHE.items(), key=lambda kv: kv[1].expires_at)[: len(_CACHE) - _CACHE_MAX_ENTRIES]:
            _CACHE.pop(key, None)


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Short TTL in-memory cache for GET /v1/advise endpoints."""

    async def dispatch(self, request: Request, call_next):
        if settings.RESPONSE_CACHE_TTL_SECONDS <= 0 or not _should_cache(request):
            return await call_next(request)

        key = _cache_key(request)

        async with _CACHE_LOCK:
            now = time.monotonic()
            entry = _CACHE.get(key)
            if entry and now < entry.expires_at:
                return Response(
                    content=entry.body,
                    status_code=entry.status_code,
                    headers={**dict(entry.headers), "X-Cache": "HIT"},
                    media_type="application/json",
                )

        response = await call_next(request)

        if response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            async with _CACHE_LOCK:
                _prune_cache(time.monotonic())
                _CACHE[key] = _CacheEntry(
                    body=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    ttl_sec=settings.RESPONSE_CACHE_TTL_SECONDS,
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

_BUCKETS: Dict[str, Tuple[float, float]] = {}   # ip -> (tokens, last_refill_ts)
_BUCKET_LOCK = asyncio.Lock()
_BUCKET_PRUNE_INTERVAL_SEC = 60.0
_BUCKET_LAST_PRUNE = 0.0
_LOOPBACK_HOSTS = frozenset({"unknown", "testclient", "127.0.0.1", "localhost", "::1"})
_UNLIMITED_PATHS = frozenset({"/v1/health", "/healthz", "/readyz", "/docs", "/redoc", "/openapi.json", "/"})


def _get_client_ip(request: Request) -> str:
    """Extracts the client IP.

    ``X-Forwarded-For`` is attacker-controlled unless a trusted reverse proxy
    overwrites it, so it is only honoured when ``TRUST_PROXY_HEADERS`` is set.
    """
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if candidate:
                return candidate
    return request.client.host if request.client else "unknown"


def _prune_buckets(now: float, burst: float, refill_rate: float) -> None:
    """Drops buckets that have fully refilled; must be called with _BUCKET_LOCK held."""
    global _BUCKET_LAST_PRUNE
    if now - _BUCKET_LAST_PRUNE < _BUCKET_PRUNE_INTERVAL_SEC:
        return
    _BUCKET_LAST_PRUNE = now
    full_after = burst / refill_rate if refill_rate > 0 else 0.0
    stale = [ip for ip, (_, last) in _BUCKETS.items() if now - last > full_after]
    for ip in stale:
        _BUCKETS.pop(ip, None)


class TokenBucketRateLimiter(BaseHTTPMiddleware):
    """Token-bucket rate limiter. Returns 429 on exhaustion.

    Bypassed for loopback/test clients and when RAILTWIN_TESTING=1.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _UNLIMITED_PATHS:
            return await call_next(request)

        ip = _get_client_ip(request)

        if ip in _LOOPBACK_HOSTS or os.environ.get("RAILTWIN_TESTING", "0") == "1":
            return await call_next(request)

        rate_limit_rpm = settings.RATE_LIMIT_RPM
        rate_limit_burst = float(settings.RATE_LIMIT_BURST)
        bucket_refill_rate = rate_limit_rpm / 60.0

        now = time.monotonic()

        async with _BUCKET_LOCK:
            _prune_buckets(now, rate_limit_burst, bucket_refill_rate)
            tokens, last_refill = _BUCKETS.get(ip, (rate_limit_burst, now))
            elapsed = now - last_refill
            tokens = min(rate_limit_burst, tokens + elapsed * bucket_refill_rate)

            if tokens < 1.0:
                _BUCKETS[ip] = (tokens, now)
                retry_after = int((1.0 - tokens) / bucket_refill_rate) + 1 if bucket_refill_rate > 0 else 60
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded: {rate_limit_rpm} req/min per IP.",
                            "retryable": True,
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            tokens -= 1.0
            _BUCKETS[ip] = (tokens, now)

        return await call_next(request)


# ---------------------------------------------------------------------------
# 3. Mutation Idempotency Middleware (F46)
# ---------------------------------------------------------------------------

_IDEMPOTENCY_CACHE: Dict[str, Tuple[int, bytes, dict, float]] = {}  # key -> (status, body, headers, expires_at)
_IDEMPOTENCY_INFLIGHT: Dict[str, asyncio.Event] = {}
_IDEMPOTENCY_LOCK = asyncio.Lock()
_IDEMPOTENCY_MAX_KEY_LENGTH = 256


def _idempotency_key(request: Request, supplied_key: str) -> str:
    """Scopes a client key to method, route, and authenticated principal."""
    auth = request.headers.get("Authorization", "")
    principal = hashlib.sha256(auth.encode("utf-8")).hexdigest() if auth else "anonymous"
    raw = f"{principal}:{request.method}:{request.url.path}:{supplied_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Guarantees mutation idempotency on POST/PUT/PATCH/DELETE when Idempotency-Key header is supplied."""

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)
        if len(idempotency_key) > _IDEMPOTENCY_MAX_KEY_LENGTH:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_IDEMPOTENCY_KEY",
                        "message": f"Idempotency-Key must be {_IDEMPOTENCY_MAX_KEY_LENGTH} characters or fewer.",
                        "retryable": False,
                    }
                },
            )

        cache_key = _idempotency_key(request, idempotency_key)
        waiter: Optional[asyncio.Event] = None
        is_leader = False

        async with _IDEMPOTENCY_LOCK:
            now = time.time()
            expired = [key for key, value in _IDEMPOTENCY_CACHE.items() if value[3] <= now]
            for key in expired:
                _IDEMPOTENCY_CACHE.pop(key, None)

            cached = _IDEMPOTENCY_CACHE.get(cache_key)
            if cached:
                status_code, body, headers, _ = cached
                return Response(
                    content=body,
                    status_code=status_code,
                    headers={**headers, "X-Idempotent-Replay": "true"},
                    media_type="application/json",
                )

            waiter = _IDEMPOTENCY_INFLIGHT.get(cache_key)
            if waiter is None:
                waiter = asyncio.Event()
                _IDEMPOTENCY_INFLIGHT[cache_key] = waiter
                is_leader = True

        # Coalesce concurrent retries for the same principal/operation. The
        # follower re-enters after the leader stores its response.
        if not is_leader:
            await waiter.wait()
            return await self.dispatch(request, call_next)

        try:
            response = await call_next(request)

            if 200 <= response.status_code < 300:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                async with _IDEMPOTENCY_LOCK:
                    _IDEMPOTENCY_CACHE[cache_key] = (
                        response.status_code,
                        body,
                        dict(response.headers),
                        time.time() + settings.IDEMPOTENCY_TTL_SECONDS,
                    )

                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json",
                )

            return response
        finally:
            async with _IDEMPOTENCY_LOCK:
                current = _IDEMPOTENCY_INFLIGHT.pop(cache_key, None)
                if current is not None:
                    current.set()
