
import pytest
from fastapi.testclient import TestClient

from api.main import app
from data.db import get_db
from engine.ops import ConnectionCustodyEngine, ConnectionTransferStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_connection_custody_evaluates_interchange():
    db = get_db()
    engine = ConnectionCustodyEngine(db)
    connections = engine.evaluate_station_connections('CNB', min_connection_time_min=15)
    assert isinstance(connections, list)
    if connections:
        conn = connections[0]
        assert isinstance(conn, ConnectionTransferStatus)
        assert conn.feeder_train_no != ''
        assert conn.connecting_train_no != ''
        assert 0.0 <= conn.connection_probability_pct <= 100.0
        assert conn.status in ('SECURE', 'AT_RISK', 'CRITICAL_MISSED', 'MISSED')
        d = conn.to_dict()
        assert 'feeder_train' in d
        assert 'connecting_train' in d
        assert 'connection_probability_pct' in d


def test_connection_custody_api_endpoint(client):
    response = client.get('/v1/stations/CNB/connections?min_transfer_min=15')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'OK'
    assert data['station_code'] == 'CNB'
    assert 'total_connections_monitored' in data
    assert 'at_risk_count' in data
    assert 'hold_advisories_active' in data
    assert isinstance(data['connections'], list)


def test_hold_advisory_structure_when_present():
    db = get_db()
    engine = ConnectionCustodyEngine(db)
    connections = engine.evaluate_station_connections('CNB', min_connection_time_min=15)
    advisories = [c for c in connections if c.hold_advisory is not None]
    for adv in advisories:
        ha = adv.hold_advisory
        assert 'action' in ha
        assert 'recommended_hold_minutes' in ha
        assert ha['recommended_hold_minutes'] > 0
        assert 'net_passenger_hours_saved' in ha
        assert ha['net_passenger_hours_saved'] > 0
        assert 'reason' in ha
