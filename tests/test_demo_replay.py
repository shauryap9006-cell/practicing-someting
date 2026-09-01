"""Determinism Verification Test Suite for RailTwin-X Replay Demo Engine (Part B / Phase B3)."""

import copy
import json
import pytest

from scripts.demo_replay import run_replay
from data.db import Database, get_db


def test_demo_replay_offline_execution():
    """Verifies that the demo replay executes all 6 timestamped events offline without external network."""
    result = run_replay(speed_multiplier=0.0, verbose=False)
    assert result is not None
    assert len(result["executed_events"]) == 6
    assert result["headline_numbers"]["attributed_delta_min"] == 16.0
    assert result["headline_numbers"]["primary_cause"] in ("WEATHER_FOG", "CONGESTION", "TSR_ACTIVE")


def test_demo_replay_strict_determinism():
    """Insurance policy test: running demo replay twice produces byte-identical event sequences and metrics."""
    run_1 = run_replay(speed_multiplier=0.0, verbose=False)
    run_2 = run_replay(speed_multiplier=0.0, verbose=False)

    # 1. Assert identical event count and offsets
    assert len(run_1["executed_events"]) == len(run_2["executed_events"])

    for ev1, ev2 in zip(run_1["executed_events"], run_2["executed_events"]):
        assert ev1["offset_seconds"] == ev2["offset_seconds"]
        assert ev1["event_type"] == ev2["event_type"]
        assert ev1["virtual_time"] == ev2["virtual_time"]

        # Delay attribution event assertions
        if ev1["event_type"] == "TRAIN_DELAY_JUMP":
            assert ev1["delay_delta_min"] == ev2["delay_delta_min"]
            assert ev1["primary_cause"] == ev2["primary_cause"]
            assert ev1["is_exact_accounting"] is True
            assert ev2["is_exact_accounting"] is True
            assert len(ev1["causes"]) == len(ev2["causes"])

            # Check cause minutes match exactly
            for c1, c2 in zip(ev1["causes"], ev2["causes"]):
                assert c1["cause_code"] == c2["cause_code"]
                assert c1["attributed_min"] == c2["attributed_min"]

        # Platform re-optimization assertions
        if ev1["event_type"] == "PLATFORM_REOPTIMIZE_TRIGGER":
            assert ev1["swaps_count"] == ev2["swaps_count"]
            assert ev1["remaining_conflicts"] == ev2["remaining_conflicts"]

    # 2. Assert headline numbers match
    assert run_1["headline_numbers"]["attributed_delta_min"] == run_2["headline_numbers"]["attributed_delta_min"]
    assert run_1["headline_numbers"]["primary_cause"] == run_2["headline_numbers"]["primary_cause"]
    assert run_1["headline_numbers"]["reopt_swaps"] == run_2["headline_numbers"]["reopt_swaps"]
