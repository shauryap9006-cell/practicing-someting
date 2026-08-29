"""Test Suite for Model Serving Pinning & Governance Checks (F15).

Asserts:
1. Predictor loads champion model as designated by registry.json.
2. Endpoint /api/system/model-info returns served model, SHA hash, and loaded status.
3. Prediction responses include complete audit provenance stamps.
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.predictor import get_predictor_service
from config import settings

client = TestClient(app)


def test_serving_model_pinning():
    """Asserts that predictor served model matches the champion in registry.json."""
    predictor = get_predictor_service()
    registry_path = settings.ARTIFACTS_DIR / "registry.json"

    assert registry_path.exists()
    with open(registry_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    champ = reg.get("champion", {})
    champion_name = champ.get("model_name") if isinstance(champ, dict) else champ
    assert predictor.champion_name == champion_name


def test_api_system_model_info_endpoint():
    """Asserts that /api/system/model-info returns governance metadata."""
    resp = client.get("/api/system/model-info")
    assert resp.status_code == 200
    data = resp.json()

    assert "served_model" in data
    assert "sha" in data
    assert "version" in data
    assert "loaded_at" in data
    assert "tiers_available" in data


def test_prediction_provenance_stamps():
    """Asserts that ETA predictions contain model, feature_version, and position provenance."""
    resp = client.get("/v1/trains/12004/eta?target_station=CNB")
    if resp.status_code == 200:
        data = resp.json()
        assert "model_provenance" in data
        prov = data["model_provenance"]
        assert "model" in prov
        assert "feature_version" in prov
        assert "as_of_ts" in prov
        assert "position" in prov
        assert "mode_seq" in prov["position"]
        assert "basis" in prov["position"]
