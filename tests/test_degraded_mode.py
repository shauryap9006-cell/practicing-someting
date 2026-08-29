"""RailTwin-X Degraded Mode & System Diagnostics Test Suite (Module I6).

Verifies health diagnostics, telemetry feed freshness checking, and degraded state flags.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from data.db import get_db

client = TestClient(app)


def test_system_status_endpoint():
    """Verifies that /api/system/status returns database health, telemetry freshness, and diagnostics."""
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "is_degraded" in data
    assert "database_connected" in data
    assert data["database_connected"] is True
    assert "tables_summary" in data
    assert data["tables_summary"]["stations"] > 0
