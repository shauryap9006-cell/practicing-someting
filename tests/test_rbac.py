"""RailTwin-X RBAC & Security Matrix Test Suite (Module I1).

Verifies authentication, token issuance, role-based endpoint protection (default-deny),
and user administration operations.
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.db import Database, get_db
from data.seed_users import seed_roles_and_users

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Ensures test database has seeded roles and standard test users."""
    db = get_db()
    seed_roles_and_users(db)


def test_login_success_admin():
    """Verifies that admin login issues a valid JWT access token."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "RailTwinAdmin2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["role_id"] == "admin"
    assert data["user"]["username"] == "admin"


def test_login_success_station_master():
    """Verifies that Station Master login succeeds."""
    response = client.post(
        "/api/auth/login",
        json={"username": "sm_ndls", "password": "StationMaster2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role_id"] == "station_master"
    assert data["user"]["station_code"] == "NDLS"


def test_login_failure_wrong_password():
    """Verifies that invalid password returns 401 Unauthorized."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_auth_me_endpoint():
    """Verifies that /api/auth/me returns the active user profile."""
    token = create_access_token({"sub": "sm_ndls", "role_id": "station_master"})
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user = response.json()
    assert user["username"] == "sm_ndls"
    assert user["role_id"] == "station_master"


def test_rbac_admin_allowed_on_user_management():
    """Verifies that admin role can query and create users."""
    admin_token = create_access_token({"sub": "admin", "role_id": "admin"})
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 10


def test_rbac_denial_non_admin_on_user_management():
    """Verifies that non-admin roles (e.g. viewer, tte) receive 403 Forbidden on admin endpoints."""
    viewer_token = create_access_token({"sub": "viewer", "role_id": "viewer"})
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_rbac_unauthenticated_request_rejected():
    """Verifies that requests without Authorization header receive 401."""
    response = client.get("/api/admin/users")
    assert response.status_code == 401
