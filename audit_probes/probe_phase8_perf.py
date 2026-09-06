import time
import os
import sys
import json
import statistics
import psutil
from datetime import datetime

# Set up paths
sys.path.insert(0, .)
sys.path.insert(0, docs)

from data.db import get_db, Database
from api.predictor import get_predictor
from ml.snapshots import SnapshotGenerator

def benchmark_8_1_and_8_4():
    proc = psutil.Process(os.getpid())
    rss_boot = proc.memory_info().rss / (1024 * 1024)
    
    predictor = get_predictor()
    # Warmup
    _ = predictor.predict_train_eta(12002, NDLS, as_of_time=2026-03-01T10:00:00)
    rss_warmed = proc.memory_info().rss / (1024 * 1024)

    latencies = []
    # 200 sequential predictions
    for i in range(200):
        t0 = time.perf_counter()
        res = predictor.predict_train_eta(12002, NDLS, as_of_time=2026-03-01T10:00:00)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0) # in ms

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    mean_lat = statistics.mean(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)

    # Continue to 500 requests for RSS measurement
    for i in range(300):
        _ = predictor.predict_train_eta(12002, NDLS, as_of_time=2026-03-01T10:00:00)
    rss_500 = proc.memory_info().rss / (1024 * 1024)

    return {
        p50_ms: round(p50, 2),
        p95_ms: round(p95, 2),
        p99_ms: round(p99, 2),
        mean_ms: round(mean_lat, 2),
        min_ms: round(min_lat, 2),
        max_ms: round(max_lat, 2),
        rss_boot_mb: round(rss_boot, 2),
        rss_warmed_mb: round(rss_warmed, 2),
        rss_500_mb: round(rss_500, 2),
        rss_delta_mb: round(rss_500 - rss_boot, 2)
    }

def benchmark_8_2_queries():
    db = get_db()
    query_count = 0
    executed_queries = []
    
    # Wrap db connection cursor execute
    orig_conn = db.get_connection
    class TracedCursor:
        def __init__(self, cur):
            self.cur = cur
        def execute(self, sql, params=()):
            nonlocal query_count
            query_count += 1
            executed_queries.append(sql.strip().replace(\n,  )[:80])
            return self.cur.execute(sql, params)
        def executemany(self, sql, seq_of_params):
            nonlocal query_count
            query_count += len(seq_of_params)
            return self.cur.executemany(sql, seq_of_params)
        def __getattr__(self, name):
            return getattr(self.cur, name)

    class TracedConn:
        def __init__(self, conn):
            self.conn = conn
        def cursor(self):
            return TracedCursor(self.conn.cursor())
        def execute(self, sql, params=()):
            nonlocal query_count
            query_count += 1
            executed_queries.append(sql.strip().replace(\n,  )[:80])
            return self.conn.execute(sql, params)
        def __getattr__(self, name):
            return getattr(self.conn, name)

    predictor = get_predictor()
    
    db.get_connection = lambda: TracedConn(orig_conn())
    
    query_count = 0
    executed_queries.clear()
    t0 = time.perf_counter()
    _ = predictor.predict_train_eta(12002, NDLS, as_of_time=2026-03-01T10:00:00)
    t1 = time.perf_counter()
    pred_cost_ms = (t1 - t0) * 1000.0
    queries_per_prediction = query_count
    pred_sample_queries = list(executed_queries)

    gen = SnapshotGenerator(db)
    query_count = 0
    executed_queries.clear()
    t0 = time.perf_counter()
    vec = gen.extract_features_at_snapshot(
        train_no=12002,
        target_station=NDLS,
        run_date_str=2026-03-01,
        query_time_iso=2026-03-01T10:00:00
    )
    t1 = time.perf_counter()
    snapshot_cost_ms = (t1 - t0) * 1000.0
    queries_per_snapshot = query_count
    snapshot_sample_queries = list(executed_queries)

    db.get_connection = orig_conn

    return {
        pred_cost_ms: round(pred_cost_ms, 2),
        queries_per_prediction: queries_per_prediction,
        pred_sample_queries: pred_sample_queries,
        snapshot_cost_ms: round(snapshot_cost_ms, 2),
        queries_per_snapshot: queries_per_snapshot,
        snapshot_sample_queries: snapshot_sample_queries
    }

if __name__ == __main__:
    b1 = benchmark_8_1_and_8_4()
    b2 = benchmark_8_2_queries()

    p50_sec = b1[p50_ms] / 1000.0
    mean_sec = b1[mean_ms] / 1000.0
    total_cpu_seconds_p50 = 10000 * p50_sec
    total_cpu_seconds_mean = 10000 * mean_sec
    required_cores_60s_p50 = total_cpu_seconds_p50 / 60.0
    required_cores_60s_mean = total_cpu_seconds_mean / 60.0

    scale_report = {
        benchmark_latency: b1,
        query_profiling: b2,
        scale_arithmetic: {
            target_trains: 10000,
            refresh_window_sec: 60,
            total_cpu_seconds_p50: round(total_cpu_seconds_p50, 2),
            total_cpu_seconds_mean: round(total_cpu_seconds_mean, 2),
            min_parallel_cores_required_p50: round(required_cores_60s_p50, 2),
            min_parallel_cores_required_mean: round(required_cores_60s_mean, 2),
            current_sqlite_single_process_lock_capacity_req_per_min: round(60.0 / mean_sec, 2),
            scale_gap_ratio: round(10000 / (60.0 / mean_sec), 2)
        }
    }

    out_path = audit_probes/phase8_perf_results.json
    with open(out_path, w) as f:
        json.dump(scale_report, f, indent=2)
    print(SUCCESS)
    print(json.dumps(scale_report, indent=2))
