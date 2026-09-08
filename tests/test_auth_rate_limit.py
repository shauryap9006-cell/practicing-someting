"""Unit tests for Authentication Rate Limiter and Account Lockout (SEC-003).

Tests:
1. 6th rapid attempt from the same IP returns 429 with Retry-After header.
2. 6th failed attempt for the same username triggers 15-minute lockout (429).
3. Successful login operates unaffected within limits.
4. Anti-enumeration: invalid-username vs wrong-password responses are byte-identical.
5. Lockouts are TTL-based and lift when expired.
"""

import pytest
from fastapi.testclient import TestClient

from api.auth_limiter import reset_auth_limiter
from api.main import app
from data.db import get_db
from data.seed_users import seed_roles_and_users

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_auth_environment():
    """Seeds test users and resets in-memory rate limiter before each test."""
    db = get_db()
    seed_roles_and_users(db)
    reset_auth_limiter()
    yield
    reset_auth_limiter()


def test_ip_rate_limit_sixth_attempt_blocked():
    """Verifies that 6th rapid login attempt from the same IP returns 429 with Retry-After."""
    ip_headers = {"X-Forwarded-For": "198.51.100.42"}

    # First 5 attempts from this IP are allowed to reach authentication
    for i in range(5):
        resp = client.post(
            "/api/auth/login",
            json={"username": f"user_{i}", "password": "WrongPassword123!"},
            headers=ip_headers,
        )
        assert resp.status_code == 401, f"Attempt {i + 1} should return 401, got {resp.status_code}"

    # 6th attempt from the same IP must be rate-limited with 429
    resp_sixth = client.post(
        "/api/auth/login",
        json={"username": "user_sixth", "password": "WrongPassword123!"},
        headers=ip_headers,
    )
    assert resp_sixth.status_code == 429
    assert "Retry-After" in resp_sixth.headers
    retry_after = int(resp_sixth.headers["Retry-After"])
    assert retry_after > 0
    assert "Too many login attempts from this IP" in resp_sixth.json()["detail"]

    # A different IP is NOT blocked
    other_ip_headers = {"X-Forwarded-For": "198.51.100.99"}
    resp_other = client.post(
        "/api/auth/login",
        json={"username": "user_other", "password": "WrongPassword123!"},
        headers=other_ip_headers,
    )
    assert resp_other.status_code == 401


def test_username_lockout_after_five_failed_attempts():
    """Verifies that 5 failed attempts for the same username trigger a 15-minute lockout (429 on 6th attempt)."""
    target_user = "admin"

    # 5 failed attempts using distinct IPs to avoid IP rate limit
    for i in range(5):
        ip_headers = {"X-Forwarded-For": f"10.0.1.{i + 1}"}
        resp = client.post(
            "/api/auth/login",
            json={"username": target_user, "password": f"BadPassword{i}"},
            headers=ip_headers,
        )
        assert resp.status_code == 401

    # 6th attempt from a fresh IP must be rejected due to account lockout
    fresh_ip_headers = {"X-Forwarded-For": "10.0.1.99"}
    resp_sixth = client.post(
        "/api/auth/login",
        json={"username": target_user, "password": "RailTwinAdmin2026!"},
        headers=fresh_ip_headers,
    )
    assert resp_sixth.status_code == 429
    assert "Retry-After" in resp_sixth.headers
    assert "Account is temporarily locked" in resp_sixth.json()["detail"]


def test_successful_login_unaffected_within_limits():
    """Verifies that authentic credentials succeed and issue tokens within normal limits."""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
        headers={"X-Forwarded-For": "10.10.10.10"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "admin"


def test_anti_enumeration_byte_identical_responses():
    """Verifies that invalid-username and wrong-password responses are byte-identical."""
    # Attempt with unknown user
    resp_unknown = client.post(
        "/api/auth/login",
        json={"username": "completely_nonexistent_user_9999", "password": "DummyPassword123!"},
        headers={"X-Forwarded-For": "10.20.20.1", "x-request-id": "anti-enum-test-id"},
    )

    # Attempt with real user but wrong password
    resp_wrong_pw = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "WrongPasswordForAdmin123!"},
        headers={"X-Forwarded-For": "10.20.20.2", "x-request-id": "anti-enum-test-id"},
    )

    assert resp_unknown.status_code == 401
    assert resp_wrong_pw.status_code == 401
    assert resp_unknown.content == resp_wrong_pw.content
    assert (
        resp_unknown.headers.get("WWW-Authenticate")
        == resp_wrong_pw.headers.get("WWW-Authenticate")
        == "Bearer"
    )


def test_lockout_expires_after_ttl(monkeypatch):
    """Verifies that lockouts are TTL-based and expire automatically."""
    import time

    current_time = 10000.0
    monkeypatch.setattr(time, "monotonic", lambda: current_time)

    # 5 failed attempts at t=10000.0
    for i in range(5):
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "WrongPassword!"},
            headers={"X-Forwarded-For": f"10.30.1.{i + 1}"},
        )
        assert resp.status_code == 401

    # Immediately locked out at t=10001.0
    current_time = 10001.0
    resp_locked = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
        headers={"X-Forwarded-For": "10.30.1.99"},
    )
    assert resp_locked.status_code == 429

    # Advance time by 901 seconds (15 minutes + 1 second)
    current_time = 10000.0 + 901.0

    # Lockout must now be lifted; valid login succeeds
    resp_unlocked = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
        headers={"X-Forwarded-For": "10.30.1.99"},
    )
    assert resp_unlocked.status_code == 200
    assert resp_unlocked.json()["user"]["username"] == "admin"
