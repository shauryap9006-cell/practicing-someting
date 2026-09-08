"""Unit tests for Forced Password Change on Seeded Accounts (SEC-004).

Tests:
1. Seeded user logins yield must_change_password=True in response and JWT token.
2. Seeded user cannot access protected non-auth endpoints (403 Forbidden).
3. Seeded user CAN access /api/auth/me and see must_change_password=True.
4. Calling /api/auth/change-password with wrong old password returns 401 Unauthorized.
5. Calling /api/auth/change-password with identical new password returns 400 Bad Request.
6. Calling /api/auth/change-password with blacklisted password returns 400 Bad Request.
7. Calling /api/auth/change-password with too short new password returns 400 or 422.
8. Valid password change clears must_change_password to 0 in DB, returns new tokens,
   and unblocks access to protected endpoints.
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
    """Ensure clean seeded environment and reset rate limiter before each test."""
    db = get_db()
    seed_roles_and_users(db)
    reset_auth_limiter()
    yield
    reset_auth_limiter()


def test_seeded_user_must_change_password_flag():
    """Seeded user login returns must_change_password=True and JWT contains the flag."""
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["user"]["must_change_password"] is True
    access_token = data["access_token"]
    assert access_token is not None

    # Verify /api/auth/me reflects must_change_password=True
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["must_change_password"] is True


def test_seeded_user_blocked_from_protected_endpoints():
    """Seeded user with must_change_password=True cannot access protected non-auth endpoints."""
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Attempt to access protected endpoint
    resp = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Password change required" in resp.json()["detail"]


def test_change_password_wrong_old_password():
    """Attempting password change with wrong old password returns 401."""
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "WrongOldPassword123!",
            "new_password": "NewSecretPassword2026#$",
        },
    )
    assert resp.status_code == 401
    assert "Current password is incorrect" in resp.json()["detail"]


def test_change_password_same_as_old():
    """Attempting to use identical old and new password returns 400."""
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "RailTwinAdmin2026!",
            "new_password": "RailTwinAdmin2026!",
        },
    )
    assert resp.status_code == 400
    assert "different from the old password" in resp.json()["detail"]


def test_change_password_blacklisted_password():
    """Attempting to set a new password that is on the blacklist returns 400."""
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "RailTwinAdmin2026!",
            "new_password": "StationMaster2026!",
        },
    )
    assert resp.status_code == 400
    assert "too common or a known default" in resp.json()["detail"]


def test_change_password_too_short():
    """Attempting to set password shorter than 10 characters returns validation error."""
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "RailTwinAdmin2026!",
            "new_password": "Short1!",
        },
    )
    assert resp.status_code in (400, 422)


def test_change_password_success_flow():
    """Successful password change clears must_change_password and unblocks protected routes."""
    # 1. Login with seeded credentials
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "sm_ndls", "password": "StationMaster2026!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert login_resp.json()["user"]["must_change_password"] is True

    # 2. Verify protected route is blocked
    blocked_resp = client.get(
        "/api/blocks/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked_resp.status_code == 403

    # 3. Change password to new secure password
    new_password = "BrandNewSecurePassword2026#$"
    change_resp = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "StationMaster2026!",
            "new_password": new_password,
        },
    )
    assert change_resp.status_code == 200
    change_data = change_resp.json()
    assert change_data["message"] == "Password updated successfully."
    assert change_data["user"]["must_change_password"] is False
    new_token = change_data["access_token"]

    # 4. Verify DB has must_change_password == 0
    db = get_db()
    with db.transaction() as cur:
        cur.execute("SELECT must_change_password FROM users WHERE username = ?", ("sm_ndls",))
        row = cur.fetchone()
        assert row["must_change_password"] == 0

    # 5. Verify protected route is now accessible with new token
    unblocked_resp = client.get(
        "/api/blocks/status",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert unblocked_resp.status_code == 200

    # 6. Verify logging in with the old password fails
    old_login = client.post(
        "/api/auth/login",
        json={"username": "sm_ndls", "password": "StationMaster2026!"},
    )
    assert old_login.status_code == 401

    # 7. Verify logging in with the new password succeeds with must_change_password=False
    new_login = client.post(
        "/api/auth/login",
        json={"username": "sm_ndls", "password": new_password},
    )
    assert new_login.status_code == 200
    assert new_login.json()["user"]["must_change_password"] is False

    # 8. Reset sm_ndls back to default seed credentials so subsequent test suites remain unaffected
    seed_roles_and_users(db)

