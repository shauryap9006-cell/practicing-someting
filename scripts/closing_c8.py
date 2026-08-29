"""C8 latency benchmark: live board p50/p95 (100 calls), journey p50/p95 (50 calls), ETA p95 with drivers (50 calls)."""
import sys, os, time, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app, raise_server_exceptions=False)

def bench(label, fn, n):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(len(times) * 0.95)]
    status = r.status_code
    print(f"[C8] {label:45s}  n={n:3d}  p50={p50:7.1f}ms  p95={p95:7.1f}ms  last_status={status}")
    return p50, p95

print("\n" + "="*80)
print("C8 · LATENCY BENCHMARKS  (baselines: live_board p50<25ms p95<155ms)")
print("="*80)

# Live board
p50_lb, p95_lb = bench("GET /api/live-board", lambda: client.get("/api/live-board"), 100)

# Journey
p50_j, p95_j = bench("GET /api/trains/2421/journey", lambda: client.get("/api/trains/2421/journey"), 50)

# ETA with drivers
p50_e, p95_e = bench("GET /v1/trains/2421/eta", lambda: client.get("/v1/trains/2421/eta"), 50)

print(f"\n[C8] VERDICT live-board  p50={p50_lb:.1f}ms ({'PASS' if p50_lb < 25 else 'FAIL'})  p95={p95_lb:.1f}ms ({'PASS' if p95_lb < 155 else 'FAIL'})")
print(f"[C8] VERDICT journey     p50={p50_j:.1f}ms  p95={p95_j:.1f}ms")
print(f"[C8] VERDICT eta-drivers p95={p95_e:.1f}ms")
print("="*80)
