"""RailTwin-X OpenWA REST Channel Adapter (Phase 2).

Sends outbound WhatsApp text alerts via self-hosted OpenWA gateway.
Zero per-message cost. Clean REST interface.
"""

from __future__ import annotations

import re
import httpx
from typing import Optional

from config import settings
from notifications.health import get_health_tracker


class OpenWAChannel:
    """Outbound WhatsApp adapter connecting to OpenWA REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        raw_url = (base_url or settings.OPENWA_URL).rstrip("/")
        self.base_url = f"{raw_url}/api" if not raw_url.endswith("/api") else raw_url
        self.api_key = api_key if api_key is not None else settings.OPENWA_API_KEY
        self.session_id = session_id or settings.OPENWA_SESSION_ID
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key

    def _normalize_phone(self, phone: str) -> str:
        """Normalizes Indian phone numbers to E.164 digits without '+' (e.g. 919876543210)."""
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            return f"91{digits}"
        if digits.startswith("91") and len(digits) == 12:
            return digits
        if digits.startswith("0") and len(digits) == 11:
            return f"91{digits[1:]}"
        return digits

    def _resolve_session_id(self) -> str:
        """Resolves session name to UUID if needed."""
        if "-" in self.session_id and len(self.session_id) == 36:
            return self.session_id
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self.base_url}/sessions", headers=self.headers)
                if r.status_code == 200:
                    for s in r.json():
                        if s.get("name") == self.session_id:
                            self.session_id = s["id"]
                            return self.session_id
        except Exception:
            pass
        return self.session_id

    def send(self, phone: str, text: str) -> bool:
        """Sends a text message to a WhatsApp number via OpenWA REST endpoint."""
        health = get_health_tracker()
        normalized_digits = self._normalize_phone(phone)
        chat_id = f"{normalized_digits}@c.us"
        resolved_sid = self._resolve_session_id()

        endpoint = f"{self.base_url}/sessions/{resolved_sid}/messages/send-text"
        payload = {
            "chatId": chat_id,
            "text": text,
        }

        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                resp = client.post(endpoint, headers=self.headers, json=payload)
                if resp.status_code < 300:
                    health.set_whatsapp_status("connected")
                    return True
                else:
                    # Gateway responded with error (e.g. session not found, QR required)
                    if resp.status_code == 404:
                        health.set_whatsapp_status("disconnected")
                    elif resp.status_code == 401 or resp.status_code == 403:
                        health.set_whatsapp_status("down", event_type="auth_failure")
                    return False
        except Exception as err:
            health.set_whatsapp_status("down", event_type=str(err))
            return False

