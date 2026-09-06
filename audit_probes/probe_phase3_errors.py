import json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Login to get admin token
login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "RailTwinAdmin2026!"})
token = login_resp.json().get("access_token")
auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

garbage_cases = [
    ("GET", "/v1/trains/99999/eta?target_station=CNB", {}, {}),
    ("GET", "/v1/trains/12301/eta?target_station=INVALID_STATION", {}, {}),
    ("GET", "/v1/trains/-123/eta?target_station=CNB", {}, {}),
    ("GET", "/v1/trains/12301/eta", {}, {}), # Missing required param
    ("GET", "/v1/trains/12301/journey", {}, {}), # Valid
    ("GET", "/v1/trains/NONEXISTENT/journey", {}, {}),
    ("GET", "/v1/trains/12301/autopsy?run_date=MALFORMED-DATE", {}, {}),
    ("GET", "/api/board/live?station_code=UNKNOWN_STATION", {}, auth_headers),
    ("POST", "/api/auth/login", {}, {}), # empty body
    ("POST", "/api/auth/login", {"username": 12345, "password": None}, {}),
    ("POST", "/api/safety/tsr", {"station_code": "NDLS", "speed_kmph": -50}, auth_headers),
    ("POST", "/v1/advise", {"train_no": "12301"}, {}),
    ("GET", "/v1/passenger/snapshot?train=UNKNOWN_TRAIN", {}, {}),
]

error_reports = []
for method, url, body, headers in garbage_cases:
    if method == "GET":
        resp = client.get(url, headers=headers)
    elif method == "POST":
        resp = client.post(url, json=body, headers=headers)
    
    try:
        content = resp.json()
    except Exception:
        content = resp.text
        
    error_reports.append({
        "method": method,
        "url": url,
        "status": resp.status_code,
        "is_500": resp.status_code >= 500,
        "response_keys": list(content.keys()) if isinstance(content, dict) else type(content).__name__,
        "sample_body": content
    })
    status_label = "CRITICAL 500" if resp.status_code >= 500 else f"HTTP {resp.status_code}"
    print(f"{method:4} {url[:45]:45} -> {status_label} (keys: {list(content.keys()) if isinstance(content, dict) else content[:30]})")

with open("audit_probes/error_sweep_results.json", "w") as f:
    json.dump(error_reports, f, indent=2)
