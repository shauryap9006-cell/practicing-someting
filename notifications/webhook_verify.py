"""RailTwin-X Inbound Webhook HMAC-SHA256 Verification (Phase 3).

Verifies the cryptographic authenticity of incoming OpenWA webhooks.
Protects `/v1/hooks/whatsapp` against spoofed or unauthorized requests.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Mapping, Optional


def verify_hmac(body: bytes, headers: Mapping[str, str], secret: Optional[str] = None) -> bool:
    """Validates HMAC-SHA256 signature against request body bytes."""
    if not secret:
        # If no secret configured in development, allow requests
        return True

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
        # If secret is set, signature header is required
        return False

    # Extract hex digest if prefixed with "sha256="
    if signature_header.startswith("sha256="):
        expected_sig = signature_header.split("=", 1)[1].strip()
    else:
        expected_sig = signature_header.strip()

    computed_sig = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)


def generate_hmac_signature(body: bytes, secret: str) -> str:
    """Helper to generate HMAC-SHA256 signature for tests and simulated payloads."""
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"
