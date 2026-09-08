"""Tests for RailTwin-X Demo & Differentiation Surface Routes.

Verifies:
1. GET /v1/model/performance returns honest horizon cards (1h tie: 5.88, 3h: 10.48, 6h: 14.80).
2. GET /v1/demo/comparator returns B1, B2, RailTwin-X cone (p10/p50/p90), error stats, and why-late.
3. POST /v1/demo/inject-event reacts dynamically and widens/shifts RailTwin-X cone.
4. POST /v1/demo/reset-events clears active shocks.
5. GET /v1/cascade/ripple returns rake links, turnaround buffer deficits, and passenger custody DSS.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_model_performance_endpoint(client):
    """Verifies that /v1/model/performance serves canonical metrics and honest 1h tie."""
    resp = client.get("/v1/model/performance")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] == "OK"
    assert data["canonical_mae"] == 10.72
    assert len(data["horizon_cards"]) == 3

    h1 = data["horizon_cards"][0]
    assert h1["horizon"] == "1h"
    assert h1["mae"] == 5.88
    assert h1["baseline_b1_mae"] == 5.84
    assert "HONEST TIE" in h1["status_badge"]

    h3 = data["horizon_cards"][1]
    assert h3["horizon"] == "3h"
    assert h3["mae"] == 10.48
    assert h3["improvement_vs_official_pct"] == 36.3

    h6 = data["horizon_cards"][2]
    assert h6["horizon"] == "6h"
    assert h6["mae"] == 14.80
    assert h6["improvement_vs_official_pct"] == 51.7


def test_demo_comparator_baseline(client):
    """Verifies comparator returns frozen line, run-rate baseline, and calibrated cone."""
    client.post("/v1/demo/reset-events")
    resp = client.get("/v1/demo/comparator?train_no=12301")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] == "OK"
    assert data["train_no"] == "12301"
    assert len(data["stations"]) > 0
    assert "active_station" in data
    assert "cumulative_errors" in data
    assert "why_late" in data
    assert data["simulation_shock_active"] is False

    # Check future stations have p10 <= p50 <= p90
    future_stns = [s for s in data["stations"] if not s["is_passed"]]
    assert len(future_stns) > 0
    for s in future_stns:
        assert s["p10_delay_min"] <= s["p50_delay_min"] <= s["p90_delay_min"]
        assert s["cone_spread_min"] > 0


def test_demo_shock_injection_and_reset(client):
    """Verifies that injecting a shock shifts RailTwin-X cone while B1/B2 stay frozen."""
    # 1. Reset first
    client.post("/v1/demo/reset-events")
    base_resp = client.get("/v1/demo/comparator?train_no=12301").json()
    base_future = [s for s in base_resp["stations"] if not s["is_passed"]][0]

    # 2. Inject operational shock: TSR 40 km/h (+25m)
    inj_resp = client.post(
        "/v1/demo/inject-event",
        json={
            "event_type": "TSR_ACTIVE",
            "station": "CNB",
            "severity_min": 25.0,
            "description": "TSR 40 km/h imposed over 35 km track replacement section",
        },
    )
    assert inj_resp.status_code == 200
    assert inj_resp.json()["status"] == "OK"

    # 3. Fetch comparator again and assert RailTwin-X reacted
    shock_resp = client.get("/v1/demo/comparator?train_no=12301").json()
    assert shock_resp["simulation_shock_active"] is True
    shock_future = [s for s in shock_resp["stations"] if not s["is_passed"]][0]

    # B1 frozen delay remains constant
    assert shock_future["b1_frozen_delay_min"] == base_future["b1_frozen_delay_min"]
    # RailTwin-X p50 and p90 widened and shifted up to account for the shock!
    assert shock_future["p50_delay_min"] > base_future["p50_delay_min"]
    assert shock_future["p90_delay_min"] > base_future["p90_delay_min"]

    # 4. Reset shocks
    reset_resp = client.post("/v1/demo/reset-events")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["active_shocks_count"] == 0

    clean_resp = client.get("/v1/demo/comparator?train_no=12301").json()
    assert clean_resp["simulation_shock_active"] is False


def test_cascade_ripple_endpoint(client):
    """Verifies /v1/cascade/ripple returns downstream rake links and passenger custody DSS."""
    resp = client.get("/v1/cascade/ripple?station_code=CNB")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] == "OK"
    assert "jurisdiction_framing" in data
    assert data["jurisdiction_framing"]["authority_badge"] == "ADVISORY ONLY"
    assert "Section Controller" in data["jurisdiction_framing"]["legal_note"]
    assert len(data["rake_turnarounds"]) > 0
    assert data["summary"]["total_rake_links_monitored"] > 0
    assert "total_net_pax_hours_saved" in data["summary"]


def test_time_machine_endpoint(client):
    """Verifies /v1/demo/time-machine serves dynamic historical snapshots from real ML & DB."""
    resp = client.get("/v1/demo/time-machine?train_no=12301&target_station=LKO")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] == "OK"
    assert data["train_no"] == "12301"
    assert "destination" in data
    assert "snapshots" in data

    snaps = data["snapshots"]
    assert "t6" in snaps and "t3" in snaps and "t1" in snaps and "truth" in snaps

    # Verify T-6h, T-3h, T-1h have real prediction strings
    for stage_id in ("t6", "t3", "t1"):
        s = snaps[stage_id]
        assert "ntes_prediction" in s
        assert "railtwin_p50" in s
        assert "railtwin_range" in s
        assert "cone_width" in s
        assert "full_receipt_hash" in s
        assert len(s["full_receipt_hash"]) == 64

    # Verify Truth arrival
    truth = snaps["truth"]
    assert "actual_arrival" in truth
    assert truth["actual_delay_min"] >= 0
    assert "GRADED_VERIFIED" in truth["ledger_state"]
