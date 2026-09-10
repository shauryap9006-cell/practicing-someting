"""WO-06 Reproducer Test: Journey N+1 Query Batching.

Verifies that GET /v1/trains/{train_no}/journey batches its database operations
into at most 2 queries (one for route stops + station info, one for station events),
rather than querying the database per-stop in a loop.
"""

from fastapi.testclient import TestClient
import pytest

from api.main import app
from data.db import get_db


def test_journey_endpoint_query_count_bounded():
    """GATE-1 Reproducer: Query counter during GET /trains/{train_no}/journey must be <= 2."""
    db = get_db()
    client = TestClient(app)

    query_count = 0
    orig_trans = db.transaction

    def counting_transaction(*args, **kwargs):
        nonlocal query_count
        query_count += 1
        return orig_trans(*args, **kwargs)

    # Wrap db.transaction to count all database transactions
    db.transaction = counting_transaction
    try:
        resp = client.get("/v1/trains/12034/journey")
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
        data = resp.json()

        # In unpatched code: query_count is ~22 because predict_train_eta is called per stop.
        # Target: <= 2 queries total (one for route stops + station info, one for station events).
        assert query_count <= 2, (
            f"N+1 Query Regression: GET /journey executed {query_count} queries (target <= 2)!"
        )

        assert len(data["timeline"]) >= 7, "Timeline must contain route stops"
        for stop in data["timeline"]:
            assert "station_code" in stop
            assert "delay_min" in stop
            assert stop["status_color"] in ["green", "amber", "red"]
            assert "band" in stop
            assert "likely_arrival" in stop["band"]
    finally:
        db.transaction = orig_trans
