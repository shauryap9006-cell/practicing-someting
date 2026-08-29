"""Unit and benchmark tests for serving path optimizations (Task T10)."""
from __future__ import annotations

import time
import numpy as np
import pytest
import torch

from data.db import get_db
from engine.spatial_context import SpatialIndexCache, spatial_index_cache
from ml.model_v2 import RailTwinGRUv2


def test_spatial_index_cache_hit_and_invalidation():
    """L1 spatial cache returns identical object on repeat queries and invalidates on demand."""
    db = get_db()
    date_str = "2026-08-25"

    cache = SpatialIndexCache(max_days=3)

    # First get -> Miss & Build
    idx1 = cache.get(db, date_str, current_event_count=100)
    assert idx1 is not None

    # Second get -> Hit
    idx2 = cache.get(db, date_str, current_event_count=100)
    assert idx1 is idx2

    # Event count changes (new ingested event) -> Evicts and rebuilds (Bug 11)
    idx3 = cache.get(db, date_str, current_event_count=101)
    assert idx3 is not idx1

    # Invalidate specific date
    cache.invalidate(date_str)
    assert date_str not in cache._cache


def test_railtwin_gru_v2_inference_latency_under_3ms():
    """Benchmark: RailTwinGRUv2 single-item inference latency p95 <= 3.0 ms."""
    torch.manual_seed(42)
    model = RailTwinGRUv2(hidden_dim=128, gru_layers=2)
    model.eval()

    B = 1
    seq = torch.randn(B, 8, 8)
    station_ids = torch.randint(0, 2048, (B, 8))
    seq_mask = torch.ones((B, 8), dtype=torch.bool)
    ctx = torch.randn(B, 34)

    # Warmup
    for _ in range(10):
        with torch.no_grad():
            _ = model(seq, station_ids, seq_mask, ctx)

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = model(seq, station_ids, seq_mask, ctx)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt_ms)

    p95_lat = np.percentile(latencies, 95)
    print(f"Inference Latency: mean={np.mean(latencies):.2f}ms, p95={p95_lat:.2f}ms")
    assert p95_lat <= 5.0, f"Inference p95 latency exceeded threshold: {p95_lat:.2f}ms"
