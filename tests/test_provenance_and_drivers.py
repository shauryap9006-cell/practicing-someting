"""RailTwin-X Provenance & Feature Attribution Drivers Tests (F17, F20, F13).

Verifies:
1. Every TrainEtaResponse carries model {name, sha256, version} provenance (F17).
2. Position record carries {mode_seq, confidence, basis, source, age_seconds} (F20).
3. Prediction carries top-3 explainability drivers {feature, contribution_min, direction} (F13).
4. Strict Pydantic schema parsing adherence in api.schemas.TrainEtaResponse.
"""

import pytest
from api.predictor import get_predictor_service
from api.schemas import TrainEtaResponse


def test_train_eta_provenance_and_drivers():
    """Asserts that predict_train_eta returns compliant provenance, position basis, and drivers."""
    predictor = get_predictor_service()
    res = predictor.predict_train_eta(train_no="2421", target_station_code="DLI")

    # 1. Model Provenance
    assert "model" in res, "Missing model provenance in prediction response"
    assert "name" in res["model"]
    assert "sha256" in res["model"]
    assert "version" in res["model"]

    # 2. Position Reconciliation
    assert "position" in res, "Missing position metadata in prediction response"
    pos = res["position"]
    assert "mode_seq" in pos
    assert "confidence" in pos
    assert "basis" in pos
    assert "source" in pos
    assert "age_seconds" in pos
    assert 0.0 <= pos["confidence"] <= 1.0

    # 3. Explainability Drivers (TreeSHAP / attribution)
    assert "drivers" in res, "Missing drivers in prediction response"
    drivers = res["drivers"]
    assert len(drivers) > 0, "Drivers list should be populated"
    assert len(drivers) <= 3, "Drivers should return top-3 most impactful drivers"

    for d in drivers:
        assert "feature" in d
        assert "contribution_min" in d
        assert d["direction"] in ["increases_delay", "decreases_delay", "neutral"]

    # 4. Strict Pydantic validation
    parsed = TrainEtaResponse.model_validate(res)
    assert parsed.train_no == "2421"
    assert parsed.model is not None
    assert parsed.position is not None
    assert len(parsed.drivers) > 0
