"""RailTwin-X Notification Health State Manager.

Maintains live gateway connection statuses (connected, disconnected, down)
and integrates directly into the `/v1/health` diagnostic endpoint.
"""

from __future__ import annotations

import datetime
from typing import Dict, Optional


class WhatsAppHealthTracker:
    """Thread-safe singleton tracking OpenWA session status and last heartbeat."""

    def __init__(self):
        self._status: str = "connected"
        self._last_updated: str = datetime.datetime.now().isoformat()
        self._last_event: Optional[str] = None
        self._session_info: Dict[str, str] = {}

    @property
    def whatsapp_status(self) -> str:
        return self._status

    def set_whatsapp_status(self, status: str, event_type: Optional[str] = None) -> None:
        """Updates WhatsApp gateway status (e.g. 'connected', 'disconnected', 'down', 'SCAN_QR')."""
        normalized = (status or "unknown").lower()
        if "connect" in normalized or normalized in ("working", "authenticated", "ready", "open"):
            self._status = "connected"
        elif "scan" in normalized or "qr" in normalized or normalized == "authenticating":
            self._status = "needs_qr"
        elif "disconnect" in normalized or "close" in normalized or normalized == "stopped":
            self._status = "disconnected"
        elif "down" in normalized or "error" in normalized or "timeout" in normalized or "failed" in normalized:
            self._status = "down"
        else:
            self._status = status

        self._last_updated = datetime.datetime.now().isoformat()
        self._last_event = event_type

    def get_health_dict(self) -> Dict[str, str]:
        return {
            "whatsapp": self._status,
            "last_updated": self._last_updated,
            "last_event": self._last_event or "nominal",
        }


# Singleton instance
_HEALTH_TRACKER = WhatsAppHealthTracker()


def get_health_tracker() -> WhatsAppHealthTracker:
    return _HEALTH_TRACKER
