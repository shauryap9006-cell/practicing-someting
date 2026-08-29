"""RailTwin-X Notification Data Types and Enums.

Defines the core AlertEvent dataclass and recipient structures for routing
operational alerts across WhatsApp, SMS, and In-App channels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NotificationSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    INAPP = "inapp"


@dataclass
class StaffRecipient:
    """Recipient resolved from the staff database table."""
    staff_id: str
    name: str
    role: str
    phone: str
    station_code: str
    on_duty: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "staff_id": self.staff_id,
            "name": self.name,
            "role": self.role,
            "phone": self.phone,
            "station_code": self.station_code,
            "on_duty": self.on_duty,
        }


@dataclass
class AlertEvent:
    """Universal notification payload routed through NotificationDispatcher."""
    severity: str  # "HIGH", "MEDIUM", "LOW"
    event_type: str  # "conflict", "crew_fatigue", "advisory", "maintenance", "system"
    title: str
    body: str
    station_code: str
    roles: List[str] = field(default_factory=lambda: ["controller"])
    train_no: Optional[str] = None
    ack_id: Optional[str] = None  # e.g. "CONF-12301-CNB" or "ADV-CNB-101"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def formatted_text(self, recipient_name: Optional[str] = None) -> str:
        """Formats clean, human-readable WhatsApp / SMS alert message with reply instructions."""
        sev_icon = "🚨" if self.severity == "HIGH" else "⚠️" if self.severity == "MEDIUM" else "ℹ️"
        lines = [
            f"{sev_icon} *RAILTWIN-X [{self.severity}]*",
        ]
        if self.train_no:
            lines.append(f"*Train:* #{self.train_no}")
        if self.station_code:
            lines.append(f"*Station/Section:* {self.station_code}")
        lines.append(f"*Alert:* {self.title}")
        if self.body:
            lines.append(f"*Details:* {self.body}")
        
        if self.ack_id:
            lines.append(
                f"\n*ACTION REQUIRED:*\nReply `ACK {self.ack_id}` to accept\nReply `ESC {self.ack_id}` to escalate/reject"
            )
        return "\n".join(lines)
