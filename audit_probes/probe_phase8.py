import time, os, sys, json, statistics, psutil, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')
sys.path.insert(0, 'docs')

from data.db import get_db, Database
from api.predictor import get_predictor_service
from ml.snapshots import SnapshotGenerator

def run():
    proc = psutil.Process(os.getpid())
    rss_boot = proc.memory_info().rss / (1024 * 1024)
    predictor = get_predictor_service()
    _ = predictor.predict_train_eta('12301', 'CNB')
    rss_warmed = proc.memory_info().rss / (1024 * 1024)

    latencies = []
    for i in range(200):
        t0 = time.perf_counter()
        _ = predictor.predict_train_eta('12301', 'CNB')
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    mean_lat = statistics.mean(latencies)

    for i in range(300):
        _ = predictor.predict_train_eta('12301', 'CNB')
    rss_500 = proc.memory_info().rss / (1024 * 1024)

    # Profiling queries
    db = get_db()
    query_count = 0
    executed_queries = []
    orig_conn = db.get_connection
    class TracedCursor:
        def __init__(self, cur):
            self.cur = cur
        def execute(self, sql, params=()):
            nonlocal query_count
            query_count += 1
            executed_queries.append(sql.strip().replace(chr(10), ' ')[:80])
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
            executed_queries.append(sql.strip().replace(chr(10), ' ')[:80])
            return self.conn.execute(sql, params)
        def __getattr__(self, name):
            return getattr(self.conn, name)

    db.get_connection = lambda: TracedConn(orig_conn())
    query_count = 0
    executed_queries.clear()
    t0 = time.perf_counter()
    _ = predictor.predict_train_eta('12301', 'CNB')
    pred_queries = query_count
    pred_sample_q = list(executed_queries)

    gen = SnapshotGenerator(db)
    query_count = 0
    executed_queries.clear()
    t0 = time.perf_counter()
    vec = gen.extract_features_at_snapshot(
        train_no='12301',
        current_seq=1,
        target_seq=5,
        run_date_str='2026-03-01',
        current_delay=12.0,
        prev_delay=8.0,
        query_time_iso='2026-03-01T10:00:00'
    )
    t1 = time.perf_counter()
    snap_cost = (t1 - t0) * 1000.0
    snap_queries = query_count
    snap_sample_q = list(executed_queries)
    db.get_connection = orig_conn

    p50_s = p50 / 1000.0
    mean_s = mean_lat / 1000.0
    total_cpu_p50 = 10000 * p50_s
    total_cpu_mean = 10000 * mean_s
    cores_60s_p50 = total_cpu_p50 / 60.0
    cores_60s_mean = total_cpu_mean / 60.0

    res = {
        'latencies_ms': {
            'min': round(min(latencies), 2),
            'p50': round(p50, 2),
            'p95': round(p95, 2),
            'p99': round(p99, 2),
            'max': round(max(latencies), 2),
            'mean': round(mean_lat, 2)
        },
        'memory_rss_mb': {
            'boot': round(rss_boot, 2),
            'warmed': round(rss_warmed, 2),
            'after_500': round(rss_500, 2),
            'delta': round(rss_500 - rss_boot, 2)
        },
        'query_counts': {
            'queries_per_predict_train_eta': pred_queries,
            'pred_sample_queries': pred_sample_q[:8],
            'snapshot_extract_features_ms': round(snap_cost, 2),
            'queries_per_snapshot': snap_queries,
            'snapshot_sample_queries': snap_sample_q[:8]
        },
        'scale_arithmetic': {
            'target_trains': 10000,
            'window_seconds': 60,
            'total_cpu_seconds_p50': round(total_cpu_p50, 2),
            'total_cpu_seconds_mean': round(total_cpu_mean, 2),
            'min_parallel_cores_p50': round(cores_60s_p50, 2),
            'min_parallel_cores_mean': round(cores_60s_mean, 2),
            'sqlite_capacity_single_proc_trains_per_min': round(60.0 / mean_s, 2),
            'scale_deficit_ratio': round(10000 / (60.0 / mean_s), 2)
        }
    }
    with open('audit_probes/phase8_perf_results.json', 'w') as f:
        json.dump(res, f, indent=2)
    print('PHASE 8 BENCHMARK COMPLETE')
    print(json.dumps(res, indent=2))

if __name__ == '__main__':
    run()
