"""RailTwin-X Multichannel Alert & Notification System.

Provides:
1. Primary WhatsApp alerting via OpenWA REST Gateway.
2. Inbound WhatsApp reply-to-ACK parsing (ACK / ESC).
3. Resilient SMS fallback for HIGH severity alerts (MSG91 / Fast2SMS / Mock).
4. Per-staff rate limiting & database-backed audit logging.
5. Real-time channel health monitoring.
"""

from notifications.types import AlertEvent, NotificationSeverity, StaffRecipient
from notifications.dispatcher import NotificationDispatcher, get_dispatcher
from notifications.health import get_health_tracker

__all__ = [
    "AlertEvent",
    "NotificationSeverity",
    "StaffRecipient",
    "NotificationDispatcher",
    "get_dispatcher",
    "get_health_tracker",
]
