import json
import re
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Login to get admin token
login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "RailTwinAdmin2026!"})
token = login_resp.json().get("access_token")
auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

endpoints_to_diff = [
    ("ETA", "/v1/trains/12301/eta?target_station=CNB", {}),
    ("Autopsy", "/v1/trains/12301/autopsy", {}),
    ("Radar", "/v1/corridor/congestion-radar", {}),
    ("Scoreboard", "/v1/ledger/scoreboard", {}),
    ("Platform States", "/api/platform/states?station_code=NDLS", auth_headers),
    ("Crew Roster", "/api/workforce/crew/roster", auth_headers),
    ("Notifications", "/api/notifications/active", auth_headers),
    ("Health", "/v1/health", {}),
    ("Model Performance", "/v1/model/performance", {}),
    ("Network State", "/v1/network/state", {}),
]

real_responses = {}
for name, url, headers in endpoints_to_diff:
    resp = client.get(url, headers=headers)
    if resp.status_code == 200:
        real_responses[name] = resp.json()
        print(f"[OK] {name} ({url}) returned 200")
    else:
        real_responses[name] = f"ERROR: HTTP {resp.status_code}"
        print(f"[FAIL] {name} ({url}) returned {resp.status_code}")

with open("audit_probes/real_responses_10.json", "w") as f:
    json.dump(real_responses, f, indent=2)

# Check datetime.now() vs datetime.utcnow() mixing in Python codebase
print("\nScanning for datetime.now() vs datetime.utcnow() mixing:")
root = Path.cwd()
py_files = list(root.glob("api/**/*.py")) + list(root.glob("engine/**/*.py")) + list(root.glob("ml/**/*.py")) + list(root.glob("data/**/*.py"))

now_calls = []
utcnow_calls = []
for p in py_files:
    text = p.read_text(encoding="utf-8", errors="ignore")
    rel = str(p.relative_to(root))
    for idx, line in enumerate(text.splitlines(), 1):
        if "datetime.utcnow(" in line or "utcnow()" in line:
            utcnow_calls.append(f"{rel}:{idx}")
        if "datetime.now(" in line:
            now_calls.append(f"{rel}:{idx}")

print(f"Total datetime.now() calls: {len(now_calls)}")
print(f"Total datetime.utcnow() calls: {len(utcnow_calls)}")
print(f"Sample datetime.utcnow() call sites (DEPRECATED & UTC-skew hazard):")
for c in utcnow_calls[:10]:
    print(f"  {c}")
