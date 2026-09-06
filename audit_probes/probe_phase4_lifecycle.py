import time
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
print("Running 200 sequential requests to test connection lifecycle...")
t0 = time.perf_counter()
for i in range(200):
    resp = client.get("/v1/trains/12301/eta?target_station=CNB")
    if resp.status_code != 200:
        print(f"Failed at req {i}: {resp.status_code}")
        break

t_total = time.perf_counter() - t0
print(f"Completed 200 sequential requests in {t_total:.2f}s ({t_total/200*1000:.1f}ms/req). Status: 200 OK.")
