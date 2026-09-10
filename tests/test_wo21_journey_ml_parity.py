"""WO-21 Reproducer Test: Restore ML Inference on Journey Endpoint.

GATES:
T1: Query count <= 2 during GET /v1/trains/{train_no}/journey.
T2: Value parity - journey per-stop predictions equal single-ETA endpoint
    predictions for the same train and future stations on a fixed fixture.
T3: Latency < 100ms for an 8-stop journey.
"""

import time
import pytest
from fastapi.testclient import TestClient

from api.main import app
from data.db import get_db


def test_wo21_journey_ml_value_parity():
    """GATE-2 VALUE PARITY: Journey per-stop predictions must equal single-ETA predictions."""
    client = TestClient(app)

    # Fetch journey timeline for fixture train 12034
    resp_journey = client.get("/v1/trains/12034/journey")
    assert resp_journey.status_code == 200
    journey_data = resp_journey.json()
    timeline = journey_data["timeline"]
    assert len(timeline) >= 7

    # Find a future stop where ML inference should run (e.g. ALJN, TDL, or GZB)
    # Stop 6: ALJN (Aligarh Junction)
    aljn_journey = next((s for s in timeline if s["station_code"] == "ALJN"), None)
    assert aljn_journey is not None

    # Compare with single-ETA endpoint
    resp_single = client.get("/v1/trains/12034/eta?station=ALJN")
    assert resp_single.status_code == 200
    single_data = resp_single.json()

    # In buggy code: aljn_journey['delay_min'] is flat carried delay (29)
    # while single_data['predicted_delay_min'] is ML ensemble prediction (52).
    assert aljn_journey["delay_min"] == single_data["predicted_delay_min"], (
        f"Value Parity Failure: journey delay ({aljn_journey['delay_min']}) != "
        f"single-ETA delay ({single_data['predicted_delay_min']})!"
    )
    assert aljn_journey["predicted_arr"] == single_data["predicted_arr"]
    assert aljn_journey["band"]["best_p10_min"] == pytest.approx(single_data["confidence_band"]["best_p10_min"], abs=0.5)
    assert aljn_journey["band"]["likely_p50_min"] == pytest.approx(single_data["confidence_band"]["likely_p50_min"], abs=0.5)
    assert aljn_journey["band"]["worst_p90_min"] == pytest.approx(single_data["confidence_band"]["worst_p90_min"], abs=0.5)


def test_wo21_journey_query_count_and_latency():
    """GATE-1 query count <= 2 and GATE-3 latency < 100ms."""
    client = TestClient(app)
    db = get_db()

    # Warmup
    client.get("/v1/trains/12034/journey")
    client.get("/v1/trains/12034/journey")

    query_count = 0
    orig_trans = db.transaction

    def counting_transaction(*args, **kwargs):
        nonlocal query_count
        query_count += 1
        return orig_trans(*args, **kwargs)

    db.transaction = counting_transaction
    try:
        t0 = time.perf_counter()
        resp = client.get("/v1/trains/12034/journey")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert resp.status_code == 200
        assert query_count <= 2, f"Query count {query_count} exceeds bound <= 2"
        # T3: Latency < 100ms for 8-stop journey
        assert elapsed_ms < 100.0, f"Latency {elapsed_ms:.1f}ms exceeds 100ms limit"
    finally:
        db.transaction = orig_trans
