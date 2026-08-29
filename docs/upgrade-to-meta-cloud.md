# 🔄 Documented Upgrade Path: Migrating from OpenWA to Meta WhatsApp Cloud API

> **Context:** RailTwin-X utilizes OpenWA for hackathon demonstration, development, and internal rail depot pilot testing (₹0 per-message cost, instant pairing with dedicated spare SIM).
> When Indian Railways moves to a formal, regulated production deployment requiring Meta Business Verification, this document provides the exact 30-line upgrade path.

---

## 1. Meta WhatsApp Cloud API Prerequisites

1. Create a [Meta Business Manager](https://business.facebook.com/) account for Indian Railways / RailTwin-X.
2. Register a dedicated phone number with WhatsApp Business Account (WABA).
3. Generate a System User Permanent Access Token (`META_WA_TOKEN`).
4. Note your Phone Number ID (`META_WA_PHONE_ID`) and WABA ID.

---

## 2. Configuration Extension (`config.py`)

Add the following environment variables to `config.py` and `.env`:

```env
WHATSAPP_PROVIDER=meta
META_WA_TOKEN=EAA...
META_WA_PHONE_ID=100654321098765
META_WA_WABA_ID=100123456789012
```

---

## 3. The 30-Line Meta Cloud Adapter (`notifications/channels/meta_cloud.py`)

Create `notifications/channels/meta_cloud.py` adhering to the exact same `send(phone, text)` interface:

```python
"""RailTwin-X Meta WhatsApp Cloud API Adapter (Regulated Production)."""

import re
import httpx
from typing import Optional
from config import settings


class MetaCloudChannel:
    """Outbound WhatsApp adapter connecting to official Meta Graph API v20.0."""

    def __init__(self, token: Optional[str] = None, phone_id: Optional[str] = None):
        self.token = token or getattr(settings, "META_WA_TOKEN", "")
        self.phone_id = phone_id or getattr(settings, "META_WA_PHONE_ID", "")
        self.url = f"https://graph.facebook.com/v20.0/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def send(self, phone: str, text: str) -> bool:
        """Sends template or free-form text to recipient phone via Meta Cloud API."""
        digits = re.sub(r"\D", "", phone)
        phone_91 = digits if digits.startswith("91") else f"91{digits}"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_91,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.url, headers=self.headers, json=payload)
                return resp.status_code < 300
        except Exception:
            return False
```

---

## 4. Dispatcher Injection (`notifications/dispatcher.py`)

In `notifications/dispatcher.py`, the channel is selected via `settings.WHATSAPP_PROVIDER`:

```python
if settings.WHATSAPP_PROVIDER == "meta":
    from notifications.channels.meta_cloud import MetaCloudChannel
    self.openwa = MetaCloudChannel()
else:
    self.openwa = OpenWAChannel()
```

---

## 5. Zero Impact on Business Logic

Because all outbound and inbound interfaces are cleanly decoupled:
- **No changes** required in conflict detection (`engine/conflicts.py`).
- **No changes** required in crew duty projections (`engine/ops.py`).
- **No changes** required in Brain advisory orchestrator (`api/brain.py`).
- **No changes** required in staff database schema or audit logs (`notification_log`, `advisory_ack_log`).
- **Inbound Webhook** simply verifies Meta's `X-Hub-Signature-256` using the exact same `verify_hmac` utility in `notifications/webhook_verify.py`.

Estimated migration execution time: **30 minutes of code swap + Meta verification turnaround.**
