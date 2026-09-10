"""WO-07 Reproducer Test: Day-Rollover and Multi-Day Arrival Correctness.

Verifies that when a train arrival rolls over midnight (either via schedule
or incurred delay), the output preserves the day offset and calendar date
rather than returning wrapped times without day indication or dropping (+1 day).
"""

import datetime
from unittest.mock import patch
import pytest

from api.predictor import PredictorService


def test_delay_midnight_rollover_preserves_day_offset():
    """GATE-1 Reproducer: Train scheduled at 23:45 with 90m delay arrives at 01:15 (+1 day)."""
    predictor = PredictorService()

    # Query 12301 at NDLS (sched_dep 16:50) to a stop where delay causes midnight rollover
    # Or call predict_train_eta with current_delay=120m on late scheduled stop
    # Train 12004: sched_arr at NDLS is 22:18.
    # With delay = 120m: 22:18 + 120m = 00:18 (+1 day)
    res = predictor.predict_train_eta(
        train_no="12004",
        target_station_code="NDLS",
        current_seq=6,
        current_delay=120.0,
    )

    # In buggy code:
    # res["predicted_arr"] returns "00:18" without any day offset indicator
    # res does not contain day_offset or predicted_arr_iso with tomorrow's date.
    assert "day_offset" in res, "day_offset field missing from prediction response!"
    assert res["day_offset"] == 1, (
        f"Expected day_offset=1 for 22:18 + 120m, but got day_offset={res['day_offset']}"
    )
    assert "+1" in res["predicted_arr"] or res["predicted_arr_iso"].endswith("+05:30"), (
        f"predicted_arr '{res['predicted_arr']}' must indicate day offset or provide valid ISO date!"
    )


def test_overnight_schedule_preserves_day_offset():
    """GATE-1 Reproducer: Overnight train schedule crossing midnight preserves day offset."""
    predictor = PredictorService()

    # Train 9410: EKNR (sched_dep 20:20) -> ADI (sched_arr 00:15 +1 day)
    res = predictor.predict_train_eta(
        train_no="9410",
        target_station_code="ADI",
        current_seq=1,
        current_delay=0.0,
    )

    # Train departs NDLS at 16:50 and reaches LKO at 04:43 next morning
    assert "day_offset" in res, "day_offset missing from response!"
    assert res["day_offset"] >= 1, (
        f"Expected day_offset >= 1 for overnight route, but got {res.get('day_offset')}"
    )
    assert "+1" in res["predicted_arr"] or "(+" in res["predicted_arr"], (
        f"predicted_arr '{res['predicted_arr']}' must indicate day offset!"
    )
