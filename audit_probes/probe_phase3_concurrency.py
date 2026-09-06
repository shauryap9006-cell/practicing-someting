import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from api.main import app
from data.db import get_db
from engine.prediction_ledger import PredictionLedger

client = TestClient(app)

routes_to_hit = [
    "/v1/trains/12301/eta?target_station=CNB",
    "/v1/trains/12301/autopsy",
    "/v1/corridor/congestion-radar",
    "/v1/ledger/scoreboard",
    "/v1/network/state",
]

def fire_request(idx):
    r_path = routes_to_hit[idx % len(routes_to_hit)]
    t0 = time.perf_counter()
    try:
        resp = client.get(r_path)
        lat = (time.perf_counter() - t0) * 1000
        return idx, r_path, resp.status_code, lat, None
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        return idx, r_path, 0, lat, str(e)

print("Firing 50 concurrent requests with ThreadPoolExecutor(max_workers=10)...")
t_start = time.perf_counter()
results = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fire_request, i) for i in range(50)]
    for fut in as_completed(futures):
        results.append(fut.result())

total_time = (time.perf_counter() - t_start) * 1000
latencies = [r[3] for r in results]
errors = [r for r in results if r[2] != 200 or r[4] is not None]

print(f"Completed 50 concurrent requests in {total_time:.1f}ms")
print(f"Latency: min={min(latencies):.1f}ms, p50={sorted(latencies)[25]:.1f}ms, max={max(latencies):.1f}ms")
print(f"Errors count: {len(errors)}")
if errors:
    for e in errors[:5]:
        print(f"  Error: {e}")

# Verify ledger chain integrity after concurrency test
db = get_db()
ledger = PredictionLedger(db)
valid, total_blocks, failed_id = ledger.verify_chain_integrity()
print(f"\nLedger verification after concurrency: valid={valid}, total_blocks={total_blocks}, failed_id={failed_id}")
