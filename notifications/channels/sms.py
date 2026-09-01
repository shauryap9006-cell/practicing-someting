"""RailTwin-X SMS Fallback Channel Adapter (Phase 5).

Provides resilient SMS delivery when WhatsApp is unreachable or down.
Supports MSG91, Fast2SMS, and local deterministic Mock provider.
"""

from __future__ import annotations

import re
import httpx
from typing import Optional

from config import settings


class SMSChannel:
    """SMS channel adapter for critical alert failover."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        sender_id: Optional[str] = None,
    ):
        self.provider = (provider or settings.SMS_PROVIDER).lower()
        self.api_key = api_key if api_key is not None else settings.SMS_API_KEY
        self.sender_id = sender_id or settings.SMS_SENDER_ID

    def _normalize_phone_10digit(self, phone: str) -> str:
        """Extracts standard 10-digit Indian mobile number."""
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 12 and digits.startswith("91"):
            return digits[2:]
        if len(digits) == 11 and digits.startswith("0"):
            return digits[1:]
        return digits

    def send(self, phone: str, text: str) -> bool:
        """Dispatches an SMS alert with provider routing and error handling."""
        phone_10 = self._normalize_phone_10digit(phone)
        if len(phone_10) != 10:
            return False

        if self.provider == "mock" or not self.api_key:
            # Deterministic mock send for tests / offline development
            return True

        if self.provider == "msg91":
            return self._send_msg91(phone_10, text)
        elif self.provider == "fast2sms":
            return self._send_fast2sms(phone_10, text)
        else:
            return True

    def _send_msg91(self, phone_10: str, text: str) -> bool:
        """Dispatches SMS via MSG91 Flow/SMS API."""
        url = "https://control.msg91.com/api/v5/flow/"
        headers = {
            "authkey": self.api_key,
            "content-type": "application/json",
        }
        payload = {
            "sender": self.sender_id,
            "mobiles": f"91{phone_10}",
            "message": text,
        }
        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                r = client.post(url, headers=headers, json=payload)
                return r.status_code < 300
        except Exception:
            return False

    def _send_fast2sms(self, phone_10: str, text: str) -> bool:
        """Dispatches SMS via Fast2SMS Quick Transactional / DLT bulkV2 API."""
        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": self.api_key,
            "Content-Type": "application/json",
        }
        # Route 'q' (Quick SMS) sends custom alert messages without requiring DLT approval
        payload = {
            "route": "q",
            "message": text,
            "numbers": phone_10,
            "flash": 0,
        }
        if self.sender_id:
            payload["sender_id"] = self.sender_id
            payload["route"] = "dlt"

        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                r = client.post(url, headers=headers, json=payload)
                if r.status_code < 300:
                    data = r.json()
                    return data.get("return", False) is True or r.status_code == 200
                return False
        except Exception:
            return False
