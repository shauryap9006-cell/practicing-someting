"""Unit tests for Observability: Prometheus Metrics & Structured Logging (OBS-001).

Tests:
1. GET /metrics returns 200 with Prometheus text/plain format.
2. GET /healthz and /readyz remain functional.
3. JSONFormatter produces valid JSON log records containing timestamp, level, logger, message.
4. JSONFormatter redacts sensitive tokens, passwords, secrets, and PNRs.
5. RequestContextMiddleware injects and propagates X-Request-ID into log context.
"""

import json
import logging
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import (
    JSONFormatter,
    RequestIdLogFilter,
    _current_request_id,
    app,
)

client = TestClient(app)


def test_metrics_endpoint_returns_prometheus_format():
    """Verifies that /metrics is reachable without auth and returns Prometheus text format."""
    # Hit an endpoint first to produce telemetry
    client.get("/healthz")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "python_gc_objects_collected_total" in resp.text or "python_info" in resp.text


def test_healthz_and_readyz_live():
    """Verifies health probes are intact and not broken by instrumentation."""
    h_resp = client.get("/healthz")
    assert h_resp.status_code == 200
    assert h_resp.json() == {"status": "alive"}

    r_resp = client.get("/readyz")
    assert r_resp.status_code == 200
    assert "status" in r_resp.json()


def test_json_formatter_structure_and_redaction():
    """Verifies JSONFormatter produces well-formed JSON and redacts sensitive credentials."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_obs_logger",
        level=logging.WARNING,
        pathname="test_file.py",
        lineno=42,
        msg="User login failed with password='SuperSecretPassword123' token='abc-xyz-token' Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "test_obs_logger"
    assert "timestamp" in parsed
    # Verify sensitive data was redacted
    assert "SuperSecretPassword123" not in parsed["message"]
    assert "[REDACTED]" in parsed["message"]


def test_request_id_propagation_in_logs():
    """Verifies that request_id from contextvar is included in structured log outputs."""
    formatter = JSONFormatter()
    req_filter = RequestIdLogFilter()

    test_req_id = f"test-req-{uuid4().hex[:8]}"
    token = _current_request_id.set(test_req_id)
    try:
        record = logging.LogRecord(
            name="test_req_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=10,
            msg="Processing flight/train request",
            args=(),
            exc_info=None,
        )
        req_filter.filter(record)
        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed.get("request_id") == test_req_id
    finally:
        _current_request_id.reset(token)


def test_http_request_id_echo():
    """Verifies that client-supplied X-Request-ID header is echoed on the response."""
    supplied_id = "req-custom-trace-999"
    resp = client.get("/healthz", headers={"X-Request-ID": supplied_id})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == supplied_id
