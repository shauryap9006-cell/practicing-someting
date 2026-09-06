import sys
import os

print("=== VERIFYING K1 ===")
try:
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.get("/v1/health")
    print(f"GET /v1/health status: {resp.status_code}")
    print(f"GET /v1/health body: {resp.json()}")
    k1_result = "FIXED" if resp.status_code == 200 else f"STILL BROKEN ({resp.status_code}: {resp.text})"
except Exception as e:
    k1_result = f"STILL BROKEN (Exception: {e})"
print(f"K1: {k1_result}\n")

print("=== VERIFYING K2 ===")
try:
    from data.db import get_db
    from engine.prediction_ledger import PredictionLedger
    db = next(get_db())
    ledger = PredictionLedger(db)
    valid, details = ledger.verify_chain_integrity()
    print(f"verify_chain_integrity result: {valid}, details: {details}")
    k2_result = "FIXED" if valid else f"STILL BROKEN (valid={valid}, details={details})"
except Exception as e:
    k2_result = f"STILL BROKEN (Exception: {e})"
print(f"K2: {k2_result}\n")
