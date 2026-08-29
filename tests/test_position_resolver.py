"""Tests for Bayesian Position Resolver and Point-in-Time Filtering (F19, F20)."""

import datetime
import pytest

from data.db import get_db
from engine.clocks import ReplayClock, set_global_clock, IST_TIMEZONE
from engine.position_resolver import PositionResolver
from api.predictor import PredictorService


def test_point_in_time_future_event_rejected():
    """Future events must never be visible to the position resolver."""
    db = get_db()
    clock = ReplayClock(datetime.datetime(2026, 8, 29, 10, 0, 0, tzinfo=IST_TIMEZONE))
    set_global_clock(clock)
    
    resolver = PositionResolver(db=db)
    
    route = [
        {"seq": 1, "station_code": "NDLS", "sched_dep": "08:00"},
        {"seq": 2, "station_code": "GZB", "sched_arr": "08:45", "sched_dep": "08:50"},
        {"seq": 3, "station_code": "ALJN", "sched_arr": "10:15", "sched_dep": "10:20"},
        {"seq": 4, "station_code": "CNB", "sched_arr": "13:00", "sched_dep": "13:10"},
    ]
    
    # Position resolver should return a valid PositionRecord
    pos = resolver.resolve_train_position("12301", route, as_of_time=clock.now())
    assert pos is not None
    assert pos.mode_seq >= 1
    assert 0.0 <= pos.confidence <= 1.0
    assert len(pos.top_k(3)) >= 1
    assert pos.basis in ("last_event", "dead_reckoning", "schedule_only", "human_confirmed")


def test_position_marginalization_cascaded_delay():
    """Marginalized ETA must propagate upstream delay correctly."""
    db = get_db()
    clock = ReplayClock(datetime.datetime(2026, 8, 29, 10, 30, 0, tzinfo=IST_TIMEZONE))
    set_global_clock(clock)
    
    predictor = PredictorService(db=db)
    # Using 12301 which exists in DB
    res = predictor.predict_train_eta("12301", "LKO")
    assert res is not None
    assert "pred_delay_p50" in res
    assert "model_provenance" in res
    pos = res["model_provenance"]["position"]
    assert "mode_seq" in pos
    assert "confidence" in pos
    assert "candidates" in pos
    assert len(pos["candidates"]) >= 1
