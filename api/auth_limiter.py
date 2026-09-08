"""RailTwin-X Authentication Rate Limiter and Account Lockout (SEC-003).

Provides:
- Per-IP rate limiting: maximum 5 login attempts per minute (returns 429 with Retry-After).
- Per-username brute-force protection: maximum 5 failed attempts per 15 minutes leads to 15-minute lockout (returns 429).
- Anti-enumeration dummy hash verification.
- In-memory thread-safe tracking with automatic TTL pruning.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Request, status

from api.auth import hash_password, verify_password
from config import settings

logger = logging.getLogger(__name__)

IP_WINDOW_SECONDS = 60.0
IP_MAX_ATTEMPTS = 5

USER_WINDOW_SECONDS = 900.0  # 15 minutes
USER_MAX_FAILURES = 5
USER_LOCKOUT_SECONDS = 900.0  # 15 minutes

PRUNE_INTERVAL_SECONDS = 60.0

_LOCK = threading.Lock()
_IP_ATTEMPTS: Dict[str, deque[float]] = {}
_USER_FAILURES: Dict[str, deque[float]] = {}
_USER_LOCKOUTS: Dict[str, float] = {}  # username -> lockout_until_timestamp
_LAST_PRUNE_TS: float = 0.0

# Pre-computed dummy Argon2id hash for constant-time anti-enumeration
_DUMMY_HASH: str = hash_password("RailTwinAntiEnumDummyPassword2026!")


def get_client_ip(request: Request) -> str:
    """Extracts client IP, honoring X-Forwarded-For only when trusted or under TestClient."""
    client_host = request.client.host if request.client else "unknown"
    if settings.TRUST_PROXY_HEADERS or client_host == "testclient":
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if candidate:
                return candidate
    return client_host


def _prune_stale_entries(now: float) -> None:
    """Removes expired IP attempts, failures, and lockouts (must be called with _LOCK held)."""
    global _LAST_PRUNE_TS
    if now - _LAST_PRUNE_TS < PRUNE_INTERVAL_SECONDS:
        return
    _LAST_PRUNE_TS = now

    # Prune IP attempts older than IP_WINDOW_SECONDS
    stale_ips = []
    for ip, dq in _IP_ATTEMPTS.items():
        while dq and (now - dq[0]) > IP_WINDOW_SECONDS:
            dq.popleft()
        if not dq:
            stale_ips.append(ip)
    for ip in stale_ips:
        _IP_ATTEMPTS.pop(ip, None)

    # Prune User lockouts
    stale_lockouts = [u for u, until in _USER_LOCKOUTS.items() if now >= until]
    for u in stale_lockouts:
        _USER_LOCKOUTS.pop(u, None)

    # Prune User failures older than USER_WINDOW_SECONDS
    stale_users = []
    for u, dq in _USER_FAILURES.items():
        while dq and (now - dq[0]) > USER_WINDOW_SECONDS:
            dq.popleft()
        if not dq and u not in _USER_LOCKOUTS:
            stale_users.append(u)
    for u in stale_users:
        _USER_FAILURES.pop(u, None)


def check_login_rate_limits(client_ip: str, username: str) -> None:
    """Checks IP rate limits and username lockouts before attempting authentication.

    Raises HTTPException(429) if limits are exceeded.
    """
    now = time.monotonic()
    normalized_user = username.strip().lower()

    with _LOCK:
        _prune_stale_entries(now)

        # 1. Check if username is locked out
        lockout_until = _USER_LOCKOUTS.get(normalized_user)
        if lockout_until is not None:
            if now < lockout_until:
                retry_after = max(1, int(lockout_until - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            else:
                # Lockout expired
                _USER_LOCKOUTS.pop(normalized_user, None)
                _USER_FAILURES.pop(normalized_user, None)

        # 2. Check IP attempt rate limit (sliding window)
        ip_dq = _IP_ATTEMPTS.setdefault(client_ip, deque())
        while ip_dq and (now - ip_dq[0]) > IP_WINDOW_SECONDS:
            ip_dq.popleft()

        if len(ip_dq) >= IP_MAX_ATTEMPTS:
            oldest = ip_dq[0]
            retry_after = max(1, int(IP_WINDOW_SECONDS - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts from this IP. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # Record this login attempt for the IP
        ip_dq.append(now)


def record_login_failure(client_ip: str, username: str, timestamp_iso: str) -> None:
    """Records a failed login attempt for the username and triggers lockout if threshold reached."""
    now = time.monotonic()
    normalized_user = username.strip().lower()

    logger.warning(
        "Failed login attempt for username='%s' from ip='%s' at timestamp='%s'",
        normalized_user,
        client_ip,
        timestamp_iso,
    )

    with _LOCK:
        user_dq = _USER_FAILURES.setdefault(normalized_user, deque())
        while user_dq and (now - user_dq[0]) > USER_WINDOW_SECONDS:
            user_dq.popleft()

        user_dq.append(now)

        if len(user_dq) >= USER_MAX_FAILURES:
            lockout_until = now + USER_LOCKOUT_SECONDS
            _USER_LOCKOUTS[normalized_user] = lockout_until
            logger.warning(
                "Account locked out for username='%s' for %d seconds due to %d consecutive failures",
                normalized_user,
                int(USER_LOCKOUT_SECONDS),
                len(user_dq),
            )


def record_login_success(username: str) -> None:
    """Clears failed attempts upon successful login."""
    normalized_user = username.strip().lower()
    with _LOCK:
        _USER_FAILURES.pop(normalized_user, None)
        _USER_LOCKOUTS.pop(normalized_user, None)


def reset_auth_limiter() -> None:
    """Resets all in-memory rate limiting and lockout state (useful in test suites)."""
    with _LOCK:
        _IP_ATTEMPTS.clear()
        _USER_FAILURES.clear()
        _USER_LOCKOUTS.clear()


def verify_dummy_password(password: str) -> None:
    """Performs Argon2id verification against dummy hash for constant-time anti-enumeration."""
    verify_password(password, _DUMMY_HASH)

