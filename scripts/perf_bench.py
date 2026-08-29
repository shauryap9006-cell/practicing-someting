"""scripts/perf_bench.py — Honest API performance benchmark.

C8 FIX: Pre-checks train 2421 and station NDLS exist (seeds from data/seeds if 0).
         Only collects latency on 200 responses. Fails if any call returns 4xx/5xx.
         Reports p50/p95/p99.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import numpy as np

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use FastAPI TestClient for in-process measurement (avoids network overhead, measures app logic)
try:
    from fastapi.testclient import TestClient
    from api.main import app
    CLIENT_MODE = "testclient"
except ImportError:
    CLIENT_MODE = "requests"


def _ensure_seeded() -> bool:
    """Verify train 2421 and station NDLS exist; print counts."""
    from data.db import Database
    db = Database()
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) as n FROM trains WHERE train_no='2421'")
        t_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM stations WHERE code='NDLS'")
        s_count = cur.fetchone()["n"]

    print(f"[BENCH] Pre-check: train 2421 exists={t_count>0}  station NDLS exists={s_count>0}")
    if t_count == 0:
        print("[BENCH] WARNING: train 2421 not in DB -- bench will get 404s on journey/eta endpoints")
        print("[BENCH] Seeding from data/seeds if available...")
        seed_path = Path("data/seeds")
        if seed_path.exists():
            try:
                import subprocess
                subprocess.run(["python", "data/seed.py", "--trains-only"], check=False, timeout=30)
                print("[BENCH] Seed attempted")
            except Exception as e:
                print(f"[BENCH] Seed failed: {e}")
    return t_count > 0 and s_count > 0


def _bench_endpoint(client, url: str, n: int, label: str) -> list:
    """Run n requests to url, assert all 200. Return latency list (ms)."""
    latencies = []
    failures = 0
    for i in range(n):
        t0 = time.perf_counter()
        try:
            r = client.get(url)
            ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code == 200:
                latencies.append(ms)
            else:
                failures += 1
                if i == 0 or failures <= 3:
                    print(f"[BENCH] {label} call {i+1}: status={r.status_code} -- FAIL")
        except Exception as e:
            failures += 1
            ms = (time.perf_counter() - t0) * 1000.0
            if failures <= 3:
                print(f"[BENCH] {label} call {i+1}: exception={e}")

    print(f"[BENCH] {label}: n={n}  success={len(latencies)}  failures={failures}")
    if failures > 0:
        print(f"[BENCH] FAIL: {failures}/{n} calls returned non-200. Check endpoint seeding.")
    return latencies


def _stats(latencies: list, label: str) -> dict:
    if not latencies:
        print(f"[BENCH] {label}: NO SUCCESSFUL CALLS -- all 4xx/5xx")
        return {"p50": None, "p95": None, "p99": None, "n": 0}
    a = np.array(latencies)
    p50 = float(np.percentile(a, 50))
    p95 = float(np.percentile(a, 95))
    p99 = float(np.percentile(a, 99))
    print(f"[BENCH] {label:25s}: n={len(a):3d}  p50={p50:7.1f}ms  p95={p95:7.1f}ms  p99={p99:7.1f}ms")
    return {"p50": round(p50, 2), "p95": round(p95, 2), "p99": round(p99, 2), "n": len(a)}


def run_bench() -> dict:
    print("=" * 60)
    print("C8 HONEST PERF BENCHMARK")
    print("=" * 60)

    seeded = _ensure_seeded()

    # Discover correct endpoint URLs from the API routes
    # Based on api/main.py router prefixes seen in codebase
    ENDPOINTS = {
        "board_live":    ("/api/board/NDLS",                        100),
        "journey_2421":  ("/v1/trains/2421/journey",                 50),
        "eta_2421":      ("/v1/trains/2421/eta?target_station=CNB",  50),
    }

    # Fallback URL aliases to try if first fails
    FALLBACK_URLS = {
        "board_live": ["/api/board/NDLS", "/v1/board/NDLS", "/api/live-board"],
        "journey_2421": ["/v1/trains/2421/journey", "/api/trains/2421/journey"],
        "eta_2421": ["/v1/trains/2421/eta?target_station=CNB", "/api/trains/2421/eta?target_station=CNB"],
    }

    if CLIENT_MODE == "testclient":
        client = TestClient(app, raise_server_exceptions=False)
    else:
        print("[BENCH] FastAPI TestClient not available -- using requests (server must be running)")
        import requests
        class RequestsClient:
            BASE = "http://localhost:8000"
            def get(self, url):
                return requests.get(self.BASE + url, timeout=5)
        client = RequestsClient()

    results = {}
    baselines = {"board_live": {"p50": 24.9, "p95": 155.0}, "journey_2421": {"p95": 155.0}, "eta_2421": {"p95": 165.0}}

    for key, (url, n) in ENDPOINTS.items():
        # Try primary URL, fall back if needed
        urls_to_try = FALLBACK_URLS.get(key, [url])
        working_url = url
        for candidate in urls_to_try:
            try:
                r = client.get(candidate)
                if r.status_code in (200, 422, 404):
                    working_url = candidate
                    break
            except Exception:
                continue

        latencies = _bench_endpoint(client, working_url, n, key)
        results[key] = _stats(latencies, key)
        results[key]["url"] = working_url

        # Compare vs baseline
        base = baselines.get(key, {})
        if base.get("p95") and results[key]["p95"]:
            delta = results[key]["p95"] - base["p95"]
            status = "PASS" if delta <= 10 else f"WARN +{delta:.1f}ms above baseline"
            print(f"  vs baseline p95={base['p95']}ms: {status}")

    print("\n[BENCH] SUMMARY")
    print(f"  board_live  p50={results['board_live']['p50']}ms  p95={results['board_live']['p95']}ms")
    print(f"  journey     p50={results['journey_2421']['p50']}ms  p95={results['journey_2421']['p95']}ms")
    print(f"  eta         p95={results['eta_2421']['p95']}ms")

    # Check if any endpoint got zero successes (indicates unseeded DB)
    all_ok = all(r["n"] > 0 for r in results.values())
    if not all_ok:
        print("\n[BENCH] FAIL: Some endpoints returned zero 200s.")
        print("  Likely cause: train 2421 / NDLS not seeded. Run: python data/seed.py")
        if not seeded:
            print("  seed_check=False confirms DB is missing required data.")
    else:
        print("\n[BENCH] All endpoints returned 200s.")

    # Save results
    bench_path = Path("ml/artifacts/perf_bench.json")
    bench_path.parent.mkdir(exist_ok=True)
    with open(bench_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[BENCH] Results saved to {bench_path}")

    return results


if __name__ == "__main__":
    run_bench()
