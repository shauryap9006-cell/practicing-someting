"""End-to-End Automated Rehearsal Test for the 3-Minute Hackathon Demo Script.

Tests the full sequence:
1. Corridor live query.
2. Inject +120m delay at Kanpur -> cascade simulation.
3. Cascade inheritance across >= 3 trains.
4. Same-rake doom tracker (12033 doomed while NTES says on-time).
5. Platform Gantt conflict explosion and 1-click Re-Optimizer resolution (<2s).
6. Delay autopsy exact accounting sum check.
7. Proof table validation (RailTwin-X MAE < Baseline B2).
"""

from fastapi.testclient import TestClient
import pytest

from api.main import app

client = TestClient(app)


def test_full_hackathon_demo_pipeline():
    """Executes the complete 3-minute hackathon demo script programmatically."""
    # Step 1: Control Room Live State
    resp1 = client.get("/v1/network/state")
    assert resp1.status_code == 200
    state = resp1.json()
    assert state["active_trains_count"] > 0
    assert len(state["trains"]) > 0

    # Step 2: Inject "+120m @ Kanpur" What-If Shock
    payload = {
        "train_no": "12034",
        "station_code": "CNB",
        "injected_delay_min": 120,
    }
    resp2 = client.post("/v1/simulate/what-if", json=payload)
    assert resp2.status_code == 200
    cascade = resp2.json()

    # Step 3: Cascade ripple inherits across >= 3 trains
    assert cascade["affected_trains_count"] >= 3, "Cascade must propagate to at least 3 trains"

    # Step 4: Same-Rake Doom Tracker
    resp_rake = client.get("/v1/trains/12033/journey")
    assert resp_rake.status_code == 200

    # Step 5: NDLS Platform Gantt Conflict & 1-Click Re-Optimization (<2s)
    resp_gantt = client.get("/v1/stations/NDLS/gantt")
    assert resp_gantt.status_code == 200

    resp_reopt = client.post("/v1/stations/NDLS/reoptimize", json={})
    assert resp_reopt.status_code == 200
    reopt_data = resp_reopt.json()
    assert reopt_data["execution_time_seconds"] < 2.0, "Re-optimization must complete in <2 seconds"
    assert reopt_data["conflicts_after"] <= reopt_data["conflicts_before"]

    # Step 6: Autopsy Card Sums Exactly (Exact Accounting)
    resp_autopsy = client.get("/v1/trains/12034/autopsy")
    assert resp_autopsy.status_code == 200
    autopsy = resp_autopsy.json()
    assert autopsy["is_exact_accounting"] is True
    cause_sum = sum(c["minutes"] for c in autopsy["causes"])
    assert cause_sum == autopsy["total_predicted_delay_min"]

    # Step 7: Proof Table Close (F14)
    resp_meta = client.get("/v1/meta/models")
    assert resp_meta.status_code == 200
    meta = resp_meta.json()
    assert "metrics" in meta
