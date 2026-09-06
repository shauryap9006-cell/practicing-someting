"""RailTwin-X Inbound Webhook HMAC-SHA256 Verification (Phase 3).

Verifies the cryptographic authenticity of incoming OpenWA webhooks.
Protects `/v1/hooks/whatsapp` against spoofed or unauthorized requests.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import threading
from typing import Mapping, Optional


_SEEN_SIGNATURES: dict[str, float] = {}
_SEEN_LOCK = threading.Lock()
_MAX_TIMESTAMP_AGE_SECONDS = 300


def verify_hmac(
    body: bytes,
    headers: Mapping[str, str],
    secret: Optional[str] = None,
    *,
    require_timestamp: bool = False,
    now: Optional[float] = None,
) -> bool:
    """Validates HMAC-SHA256 and, for webhooks, freshness and replay protection."""
    if not secret:
        return False

    # Search for signature in standard headers (case-insensitive)
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    signature_header = (
        normalized_headers.get("x-openwa-signature")
        or normalized_headers.get("x-hub-signature-256")
        or normalized_headers.get("x-signature-256")
        or normalized_headers.get("x-signature")
        or ""
    )

    if not signature_header:
        return False

    # Extract hex digest if prefixed with "sha256="
    if signature_header.startswith("sha256="):
        expected_sig = signature_header.split("=", 1)[1].strip()
    else:
        expected_sig = signature_header.strip()

    timestamp = normalized_headers.get("x-webhook-timestamp") or normalized_headers.get("x-openwa-timestamp")
    signed_body = body
    if require_timestamp:
        if not timestamp:
            return False
        try:
            timestamp_value = float(timestamp)
        except ValueError:
            return False
        current_time = time.time() if now is None else now
        if abs(current_time - timestamp_value) > _MAX_TIMESTAMP_AGE_SECONDS:
            return False
        signed_body = timestamp.encode("utf-8") + b"." + body

    computed_sig = hmac.new(
        secret.encode("utf-8"),
        signed_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_sig, expected_sig):
        return False

    if require_timestamp:
        replay_key = f"{timestamp}:{expected_sig}"
        current_time = time.time() if now is None else now
        with _SEEN_LOCK:
            expired = [key for key, expires_at in _SEEN_SIGNATURES.items() if expires_at <= current_time]
            for key in expired:
                _SEEN_SIGNATURES.pop(key, None)
            if replay_key in _SEEN_SIGNATURES:
                return False
            _SEEN_SIGNATURES[replay_key] = current_time + _MAX_TIMESTAMP_AGE_SECONDS

    return True


def generate_hmac_signature(body: bytes, secret: str, timestamp: Optional[str] = None) -> str:
    """Generates a body signature or timestamp-bound webhook signature."""
    signed_body = timestamp.encode("utf-8") + b"." + body if timestamp is not None else body
    sig = hmac.new(secret.encode("utf-8"), signed_body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"
