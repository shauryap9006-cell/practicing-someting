import torch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# 1. Hit /v1/trains/{no}/eta with non-existent train
resp1 = client.get("/v1/trains/99999/eta?target_station=CNB")
print(f"Non-existent train status: {resp1.status_code}")
print(f"Non-existent train body: {resp1.json()}")

# 2. Hit /v1/trains/{no}/eta with existing train but unknown station
resp2 = client.get("/v1/trains/12301/eta?target_station=XYZ_NON_EXISTENT")
print(f"\nUnknown station status: {resp2.status_code}")
print(f"Unknown station body: {resp2.json()}")

# 3. Test GRU model with NaN input
from api.predictor import get_predictor_service
ps = get_predictor_service()
nan_tensor = torch.tensor([[[float('nan')]*8]*8], dtype=torch.float32)
try:
    with torch.no_grad():
        out = ps._gru_model(nan_tensor)
    print(f"\nGRU with NaN input outputs: {out}")
except Exception as e:
    print(f"\nGRU with NaN input threw: {e}")
