import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.passenger_routes import _SNAPSHOT_CACHE
from api.predictor import get_predictor_service
from engine.prediction_ledger import PredictionLedger


@pytest.fixture(autouse=True)
def clear_cache():
    _SNAPSHOT_CACHE.clear()
    yield
    _SNAPSHOT_CACHE.clear()


def test_passenger_snapshot_has_band():
    client = TestClient(app)
    res = client.get("/v1/passenger/snapshot?train=12301")
    assert res.status_code == 200
    data = res.json()
    assert "band" in data
    band = data["band"]
    assert band["p10_min"] is not None
    assert band["p50_min"] is not None
    assert band["p90_min"] is not None
    assert "p10_time" in band
    assert "p90_time" in band
    assert "model" in data
    assert "version" in data["model"]
    assert "horizon_min" in data["model"]


def test_passenger_snapshot_seals_ledger():
    ledger = PredictionLedger()
    valid, initial_count, _ = ledger.verify_chain_integrity()
    assert valid is True

    client = TestClient(app)
    res = client.get("/v1/passenger/snapshot?train=12301")
    assert res.status_code == 200

    valid, new_count, _ = ledger.verify_chain_integrity()
    assert valid is True
    assert new_count == initial_count + 1


def test_passenger_debounce_cache(monkeypatch):
    predictor = get_predictor_service()
    real_predict = predictor.predict_train_eta
    call_count = 0

    def mock_predict(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return real_predict(*args, **kwargs)

    monkeypatch.setattr(predictor, "predict_train_eta", mock_predict)

    ledger = PredictionLedger()
    valid, initial_count, _ = ledger.verify_chain_integrity()
    assert valid is True

    client = TestClient(app)

    # First call - cache miss
    res1 = client.get("/v1/passenger/snapshot?train=12301")
    assert res1.status_code == 200
    assert call_count == 1

    # Second rapid call - cache hit
    res2 = client.get("/v1/passenger/snapshot?train=12301")
    assert res2.status_code == 200
    assert call_count == 1  # Debounced: no second predictor call

    valid, after_count, _ = ledger.verify_chain_integrity()
    assert valid is True
    assert after_count == initial_count + 1  # Exactly 1 ledger block sealed


def test_passenger_unknown_train():
    client = TestClient(app)
    res = client.get("/v1/passenger/snapshot?train=99999")
    assert res.status_code == 404
    err = res.json()
    assert err["detail"]["code"] == "TRAIN_NOT_FOUND"
