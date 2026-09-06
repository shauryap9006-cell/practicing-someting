import time
from fastapi.testclient import TestClient

t0 = time.perf_counter()
from api.main import app
t_import = time.perf_counter() - t0

client = TestClient(app)

# 1. First request latency vs steady state
t_start = time.perf_counter()
r1 = client.get("/v1/health")
t_first = (time.perf_counter() - t_start) * 1000

t_start = time.perf_counter()
r2 = client.get("/v1/health")
t_second = (time.perf_counter() - t_start) * 1000

print(f"Import time: {t_import*1000:.1f}ms")
print(f"First request latency (/v1/health): {t_first:.1f}ms (HTTP {r1.status_code})")
print(f"Second request latency (/v1/health): {t_second:.1f}ms (HTTP {r2.status_code})")

# Login to get JWT token for authenticated routes
login_resp = client.post("/api/auth/login", json={"badge_number": "SM-101", "pin": "1234"})
token = login_resp.json().get("access_token") if login_resp.status_code == 200 else None
auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
print(f"Auth login status: {login_resp.status_code}, token acquired: {bool(token)}")

test_routes = [
    ("GET", "/healthz", {}),
    ("GET", "/readyz", {}),
    ("GET", "/v1/health", {}),
    ("GET", "/v1/meta/stations", {}),
    ("GET", "/v1/meta/trains", {}),
    ("GET", "/v1/meta/models", {}),
    ("GET", "/v1/trains/12301/eta?target_station=CNB", {}),
    ("GET", "/v1/trains/12301/journey", {}),
    ("GET", "/v1/trains/12301/autopsy", {}),
    ("GET", "/v1/corridor/congestion-radar", {}),
    ("GET", "/v1/ledger/scoreboard", {}),
    ("GET", "/v1/ledger/verify", {}),
    ("GET", "/v1/model/performance", {}),
    ("GET", "/v1/network/state", {}),
    ("GET", "/v1/passenger/tracker/12301", {}),
    ("GET", "/v1/passenger/popular", {}),
    ("GET", "/api/board/station?station_code=NDLS", auth_headers),
    ("GET", "/api/platform/states?station_code=NDLS", auth_headers),
    ("GET", "/api/blocks/status", auth_headers),
    ("GET", "/api/safety/tsr", auth_headers),
    ("GET", "/api/safety/incidents", auth_headers),
    ("GET", "/api/workforce/crew/roster", auth_headers),
    ("GET", "/api/timetable/versions", auth_headers),
    ("GET", "/api/audit/logs", auth_headers),
    ("GET", "/api/system/status", auth_headers),
]

sweep_results = []
for method, path, headers in test_routes:
    t_req = time.perf_counter()
    if method == "GET":
        resp = client.get(path, headers=headers)
    elif method == "POST":
        resp = client.post(path, headers=headers)
    elapsed = (time.perf_counter() - t_req) * 1000
    
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    top_keys = list(body.keys()) if isinstance(body, dict) else (f"list[{len(body)}]" if isinstance(body, list) else type(body).__name__)
    sweep_results.append({
        "method": method,
        "path": path,
        "status": resp.status_code,
        "time_ms": round(elapsed, 2),
        "keys": top_keys
    })
    print(f"{method:4} {path[:45]:45} -> {resp.status_code} ({elapsed:6.1f}ms) Keys: {top_keys}")

import json
with open("audit_probes/route_sweep_results.json", "w") as f:
    json.dump(sweep_results, f, indent=2)
