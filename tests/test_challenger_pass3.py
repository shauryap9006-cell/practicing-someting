"""Challenger 1 Pass 3 Live API Verification & Adversarial Stress Tests.

Empirical verification for:
1. POST /api/platform/reoptimize conflict resolution metrics & PlatformManager integration.
2. GET /v1/trains/{id}/autopsy exact causal delay accounting.
3. Router mounting verification across /api/infrastructure, /api/infra, /api/section, /api/coordination, /v1, /api/v1.
4. Adversarial edge cases:
   - Station codes: 'INVALID', '', null/None
   - Trains with no events or non-existent trains
   - Dispatcher ACK invalid strings and schemas
"""

import json
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.auth import create_access_token
from data.db import get_db
from data.seed_users import seed_roles_and_users

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def setup_test_environment():
    db = get_db()
    seed_roles_and_users(db)


def get_admin_headers():
    token = create_access_token({"sub": "admin", "role_id": "admin"})
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. Platform Re-optimization Empirical Verification
# ============================================================================
def test_platform_reoptimize_contract_and_stats():
    """Verify POST /api/platform/reoptimize returns all required conflict stats."""
    headers = get_admin_headers()
    resp = client.post("/api/platform/reoptimize", headers=headers, json={"station_code": "CNB"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Verify required keys
    required_keys = [
        "status",
        "station_code",
        "conflicts_before",
        "conflicts_after",
        "resolvedCount",
        "swapsCount",
        "swaps_performed",
        "execution_time_seconds",
        "message",
        "blocks",
    ]
    for key in required_keys:
        assert key in data, f"Missing key '{key}' in reoptimize response: {data.keys()}"

    assert data["status"] == "success"
    assert data["station_code"] == "CNB"
    assert isinstance(data["conflicts_before"], int)
    assert isinstance(data["conflicts_after"], int)
    assert isinstance(data["resolvedCount"], int)
    assert isinstance(data["swapsCount"], int)
    assert isinstance(data["execution_time_seconds"], (int, float))
    assert isinstance(data["blocks"], list)
    assert data["resolvedCount"] == data["conflicts_before"] - data["conflicts_after"]
    assert data["swapsCount"] == len(data["swaps_performed"])


def test_platform_reoptimize_default_and_ndls():
    """Verify POST /api/platform/reoptimize with empty payload and NDLS station."""
    headers = get_admin_headers()

    # Empty payload -> defaults to CNB
    resp_empty = client.post("/api/platform/reoptimize", headers=headers, json={})
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["station_code"] == "CNB"

    # NDLS station
    resp_ndls = client.post("/api/platform/reoptimize", headers=headers, json={"station_code": "NDLS"})
    assert resp_ndls.status_code == 200
    data_ndls = resp_ndls.json()
    assert data_ndls["station_code"] == "NDLS"
    assert "resolvedCount" in data_ndls
    assert "swapsCount" in data_ndls


# ============================================================================
# 2. Delay Autopsy Exact Accounting Empirical Verification
# ============================================================================
def test_delay_autopsy_exact_accounting():
    """Verify GET /v1/trains/{id}/autopsy returns exact causal accounting."""
    train_ids = ["12034", "12002", "12424", "12302"]
    for train_id in train_ids:
        resp = client.get(f"/v1/trains/{train_id}/autopsy")
        assert resp.status_code == 200, f"Train {train_id} autopsy failed: {resp.text}"
        data = resp.json()

        assert data["train_no"] == train_id
        assert "train_name" in data
        assert "total_predicted_delay_min" in data
        assert "is_exact_accounting" in data
        assert "causes" in data
        assert "updated_at" in data
        assert "clock_mode" in data

        # Exact causal accounting verification: sum(cause.minutes) must match total_predicted_delay_min
        causes_sum = sum(c["minutes"] for c in data["causes"])
        assert causes_sum == data["total_predicted_delay_min"], (
            f"Causal accounting mismatch for train {train_id}: "
            f"causes sum {causes_sum} != total {data['total_predicted_delay_min']}"
        )


# ============================================================================
# 3. Router Mounting & Prefix Verification
# ============================================================================
def test_router_mounting_no_404s_or_double_prefixes():
    """Verify all mounted prefixes and key routes resolve without 404s or double prefixes."""
    headers = get_admin_headers()

    endpoints_to_test = [
        # /api/infrastructure
        ("GET", "/api/infrastructure/rakes", 200),
        ("GET", "/api/infrastructure/assets", 200),
        ("GET", "/api/infrastructure/feedback", 200),
        # /api/infra (alias prefix)
        ("GET", "/api/infra/rakes", 200),
        ("GET", "/api/infra/assets", 200),
        ("GET", "/api/infra/feedback", 200),
        # /api/section
        ("GET", "/api/section/corridor", 200),
        ("GET", "/api/section/precedence", 200),
        # /api/coordination (alias prefix)
        ("GET", "/api/coordination/corridor", 200),
        ("GET", "/api/coordination/precedence", 200),
        # /v1
        ("GET", "/v1/health", 200),
        ("GET", "/v1/network/state", 200),
        ("GET", "/v1/meta/stations", 200),
        ("GET", "/v1/meta/trains", 200),
        ("GET", "/v1/meta/models", 200),
        ("GET", "/v1/crew/alerts", 200),
        ("GET", "/v1/trains/12034/eta?station=NDLS", 200),
        ("GET", "/v1/trains/12034/journey", 200),
        ("GET", "/v1/trains/12034/autopsy", 200),
        ("GET", "/v1/stations/NDLS/gantt", 200),
        ("POST", "/v1/stations/NDLS/reoptimize", 200),
        # /api/v1
        ("GET", "/api/v1/health", 200),
        ("GET", "/api/v1/network/state", 200),
        ("GET", "/api/v1/meta/stations", 200),
        ("GET", "/api/v1/trains/12034/autopsy", 200),
        # /api/platform
        ("GET", "/api/platform/states?station_code=NDLS", 200),
        ("POST", "/api/platform/reoptimize", 200),
    ]

    for method, path, expected_status in endpoints_to_test:
        if method == "GET":
            resp = client.get(path, headers=headers)
        elif method == "POST":
            resp = client.post(path, headers=headers, json={})
        assert resp.status_code == expected_status, (
            f"Endpoint {method} {path} returned status {resp.status_code} (expected {expected_status}): {resp.text}"
        )


def test_openapi_schema_no_double_prefixes():
    """Verify OpenAPI schema paths have no double prefixes like /api/infrastructure/api/..."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    invalid_patterns = [
        "/api/infrastructure/api",
        "/api/infra/api",
        "/api/section/api",
        "/api/coordination/api",
        "/v1/v1",
        "/api/v1/v1",
        "//",
    ]

    for path in paths.keys():
        for pattern in invalid_patterns:
            assert pattern not in path, f"Detected malformed / double-prefix path in OpenAPI: '{path}' (matched '{pattern}')"


# ============================================================================
# 4. Adversarial Edge Cases
# ============================================================================
def test_platform_reoptimize_adversarial_station_inputs():
    """Verify POST /api/platform/reoptimize handles invalid, empty, and null station codes gracefully."""
    headers = get_admin_headers()

    # Case A: Non-existent station code -> Should return 200 with 0 blocks / 0 conflicts
    resp_invalid = client.post("/api/platform/reoptimize", headers=headers, json={"station_code": "INVALID_STN_999"})
    assert resp_invalid.status_code == 200
    data_invalid = resp_invalid.json()
    assert data_invalid["station_code"] == "INVALID_STN_999"
    assert data_invalid["conflicts_before"] == 0
    assert data_invalid["conflicts_after"] == 0
    assert data_invalid["resolvedCount"] == 0
    assert data_invalid["swapsCount"] == 0
    assert data_invalid["blocks"] == []

    # Case B: Empty string station code -> Defaults gracefully to CNB
    resp_empty_stn = client.post("/api/platform/reoptimize", headers=headers, json={"station_code": ""})
    assert resp_empty_stn.status_code == 200
    data_empty_stn = resp_empty_stn.json()
    assert data_empty_stn["station_code"] == "CNB"

    # Case C: Null station code -> Defaults gracefully to CNB
    resp_null_stn = client.post("/api/platform/reoptimize", headers=headers, json={"station_code": None})
    assert resp_null_stn.status_code == 200
    data_null_stn = resp_null_stn.json()
    assert data_null_stn["station_code"] == "CNB"

    # Case D: Null request body
    resp_null_body = client.post("/api/platform/reoptimize", headers=headers)
    assert resp_null_body.status_code == 200
    assert resp_null_body.json()["station_code"] == "CNB"


def test_delay_autopsy_edge_cases():
    """Verify GET /v1/trains/{id}/autopsy with edge case trains."""
    # Case A: Non-existent train -> 404
    resp_nonexistent = client.get("/v1/trains/NON_EXISTENT_TRAIN/autopsy")
    assert resp_nonexistent.status_code == 404
    data_err = resp_nonexistent.json()
    assert "TRAIN_NOT_FOUND" in str(data_err)

    # Case B: Synthetic train with no events in DB
    db = get_db()
    with db.transaction() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO trains (train_no, name, class, priority) VALUES (?, ?, ?, ?)",
            ("99991", "Test Ghost Express", "special", 1),
        )
    try:
        resp_ghost = client.get("/v1/trains/99991/autopsy")
        assert resp_ghost.status_code == 200
        data_ghost = resp_ghost.json()
        assert data_ghost["train_no"] == "99991"
        assert data_ghost["total_predicted_delay_min"] == 0
        assert data_ghost["is_exact_accounting"] is False
        assert data_ghost["causes"] == []
    finally:
        with db.transaction() as cur:
            cur.execute("DELETE FROM trains WHERE train_no = '99991'")


def test_dispatcher_ack_validation_and_rejection():
    """Verify POST /v1/advise/{adv_id}/ack validation on decisions and schemas."""
    # Case A: Valid 'accepted'
    resp_acc = client.post("/v1/advise/adv-test-101/ack", json={"decision": "accepted", "dispatcher_id": "D1"})
    assert resp_acc.status_code == 200
    assert resp_acc.json()["decision"] == "accepted"

    # Case B: Valid 'rejected'
    resp_rej = client.post("/v1/advise/adv-test-102/ack", json={"decision": "rejected", "comment": "Conflict manual override"})
    assert resp_rej.status_code == 200
    assert resp_rej.json()["decision"] == "rejected"

    # Case C: Invalid decision string value -> 400 rejection (or 422)
    resp_inv = client.post("/v1/advise/adv-test-103/ack", json={"decision": "maybe_later"})
    assert resp_inv.status_code in (400, 422), f"Expected 400 or 422, got {resp_inv.status_code}: {resp_inv.text}"

    # Case D: Missing required decision field -> 422 Unprocessable Entity
    resp_missing = client.post("/v1/advise/adv-test-104/ack", json={"comment": "No decision provided"})
    assert resp_missing.status_code == 422, f"Expected 422 for missing required field, got {resp_missing.status_code}"

    # Case E: Extra fields forbidden -> 422 Unprocessable Entity
    resp_extra = client.post("/v1/advise/adv-test-105/ack", json={"decision": "accepted", "unsupported_field": 123})
    assert resp_extra.status_code == 422, f"Expected 422 for extra forbidden field, got {resp_extra.status_code}"
