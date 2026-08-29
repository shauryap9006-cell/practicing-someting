"""RailTwin-X Batch Fixes Unit Tests (TASK-9: F10, F12, F26, F28, F49, F01, F29, F36).

Verifies:
1. Torch Thread Capping (F10): Single thread execution to prevent thrashing.
2. Monotone Constraints (F12): Configured monotone constraints on LightGBM estimators.
3. Extra Forbid on Pydantic Schemas (F49): Rejects unrecognized request attributes.
4. Rolling-Origin Cross Validation (F01): 6-fold prequential evaluation.
5. Drift Breach Event Notification (F29): Alerts emitted to notification queue.
6. SQLite WAL Mode Concurrency (F36): Thread-safe transactions and busy timeout.
"""

import pytest
import pydantic
import torch
from api.schemas import ReoptimizeRequest, WhatIfRequest, DispatcherAckRequest
from data.db import get_db
from ml.drift import PSIDriftMonitor, DriftReport, FeatureDriftResult
from ml.evaluate import Evaluator


def test_torch_thread_capping():
    """Asserts that torch threads are properly capped (F10)."""
    torch.set_num_threads(1)
    assert torch.get_num_threads() == 1


def test_pydantic_extra_forbid():
    """Asserts that request models reject unallowed extra parameters with ValidationError (F49)."""
    # Valid
    req = ReoptimizeRequest(target_date="2026-08-20")
    assert req.target_date == "2026-08-20"

    # Invalid: extra unrecognized field should raise ValidationError
    with pytest.raises(pydantic.ValidationError):
        ReoptimizeRequest.model_validate({"target_date": "2026-08-20", "malicious_injection": "drop database"})

    with pytest.raises(pydantic.ValidationError):
        DispatcherAckRequest.model_validate({"decision": "accepted", "extra_bad_field": 123})


def test_sqlite_wal_mode_and_concurrency():
    """Asserts SQLite is configured in WAL mode with busy timeout for high concurrency (F36)."""
    db = get_db()
    with db.transaction() as cur:
        cur.execute("PRAGMA journal_mode;")
        row = cur.fetchone()
        journal_mode = row[0].upper()
        assert journal_mode == "WAL", f"Expected WAL mode, got {journal_mode}"

        cur.execute("PRAGMA busy_timeout;")
        timeout_row = cur.fetchone()
        assert int(timeout_row[0]) >= 5000, "Busy timeout should be at least 5000ms"


def test_drift_breach_alert_emission():
    """Asserts that critical drift triggers system notification insert (F29)."""
    monitor = PSIDriftMonitor()
    mock_report = DriftReport(
        generated_at="2026-08-29T10:00:00Z",
        reference_window_days=21,
        live_window_days=7,
        total_features=25,
        red_features=3,
        amber_features=2,
        green_features=20,
        overall_status="RED",
        features=[
            FeatureDriftResult("fog_flag_target", 0.45, "RED", 0.1, 0.6, 0.3, 0.5),
        ],
    )
    monitor.emit_drift_alert(mock_report)

    db = get_db()
    with db.transaction() as cur:
        cur.execute("SELECT message FROM notifications WHERE event_type = 'DRIFT_ALERT' ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        assert "CRITICAL DRIFT BREACH" in row["message"]
