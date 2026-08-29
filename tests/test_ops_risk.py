"""Unit and benchmark tests for Risk-Aware Re-Optimizer (Task T8)."""
from __future__ import annotations

import datetime
import pytest

from engine.ops_risk import RiskPlatformBlock, RiskAwareReOptimizer


def test_cvar_overlap_computation():
    """Worst-case tail overlap is calculated when 95% quantile uncertainty intervals overlap."""
    b1 = RiskPlatformBlock(
        train_no="12301",
        platform=1,
        sched_arr_iso="2026-08-25T10:00:00+05:30",
        dwell_min=10,
        delay_q10=0.0,
        delay_q50=5.0,
        delay_q95=20.0,  # [10:00 to 10:30]
        priority=2,
    )
    b2 = RiskPlatformBlock(
        train_no="12302",
        platform=1,
        sched_arr_iso="2026-08-25T10:15:00+05:30",
        dwell_min=10,
        delay_q10=0.0,
        delay_q50=5.0,
        delay_q95=15.0,  # [10:15 to 10:40]
        priority=1,
    )

    cost = b1.cvar_overlap(b2)
    assert cost > 0.0, "Expected positive CVaR overlap cost"


def test_risk_reoptimizer_resolves_conflicts_and_satisfies_guarantee():
    """Optimizer reassigns platforms to minimize total risk cost and never degrades incumbent."""
    reopt = RiskAwareReOptimizer(swap_penalty=5.0)

    # 3 trains competing for platform 1
    blocks = [
        RiskPlatformBlock("T1", 1, "2026-08-25T10:00:00+05:30", 15, 0.0, 5.0, 20.0),
        RiskPlatformBlock("T2", 1, "2026-08-25T10:10:00+05:30", 15, 0.0, 5.0, 20.0),
        RiskPlatformBlock("T3", 1, "2026-08-25T10:20:00+05:30", 15, 0.0, 5.0, 20.0),
    ]

    opt_blocks, diff = reopt.optimize("NDLS", blocks, available_platforms=[1, 2, 3])

    assert diff.conflicts_after < diff.conflicts_before
    assert diff.cost_optimized <= diff.cost_incumbent
    assert diff.guarantee_satisfied is True
    assert diff.execution_time_ms < 40.0


def test_risk_reoptimizer_latency_benchmark_20_trains():
    """Benchmark: 20-train station graph executes within 40ms SLA."""
    reopt = RiskAwareReOptimizer()

    blocks = []
    base_time = datetime.datetime(2026, 8, 25, 10, 0, 0)
    for i in range(20):
        t_arr = (base_time + datetime.timedelta(minutes=i * 5)).isoformat() + "+05:30"
        blocks.append(
            RiskPlatformBlock(
                train_no=f"T{i:03d}",
                platform=(i % 3) + 1,  # 3 platforms overloaded
                sched_arr_iso=t_arr,
                dwell_min=10,
                delay_q10=0.0,
                delay_q50=5.0,
                delay_q95=15.0,
            )
        )

    _, diff = reopt.optimize("NDLS", blocks, available_platforms=list(range(1, 11)))
    assert diff.execution_time_ms <= 40.0, f"Exceeded 40ms SLA: {diff.execution_time_ms:.2f}ms"
    assert diff.acceptance_rate >= 0.0
    assert diff.cost_optimized <= diff.cost_incumbent
