"""RailTwin-X OpenWA Bootstrap & Webhook Registration Script.

One-shot utility to:
1. Authenticate with OpenWA gateway on port 2785.
2. Initialize and start 'railtwin-alerts' session.
3. Save and display login QR code for pairing the WhatsApp phone.
4. Register the inbound webhook at '{PUBLIC_URL}/v1/hooks/whatsapp'.
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
from pathlib import Path
import httpx

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings


def setup_openwa() -> bool:
    base_url = settings.OPENWA_URL.rstrip("/")
    api_base = f"{base_url}/api" if not base_url.endswith("/api") else base_url
    api_key = settings.OPENWA_API_KEY
    session_name = settings.OPENWA_SESSION_ID
    webhook_url = f"{settings.PUBLIC_URL}/v1/hooks/whatsapp"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    print("=" * 70)
    print("📱 RAILTWIN-X: OPENWA GATEWAY SETUP & PAIRING")
    print("=" * 70)
    print(f"OpenWA URL:      {base_url}")
    print(f"API Key:         {api_key[:12]}..." if api_key else "API Key: (None)")
    print(f"Session Name:    {session_name}")
    print(f"Inbound Webhook: {webhook_url}")
    print("=" * 70)

    with httpx.Client(timeout=30.0) as client:
        # 1. Check Gateway & List Sessions
        print("\n[STEP 1/4] Checking OpenWA Gateway connectivity...")
        try:
            r = client.get(f"{api_base}/sessions", headers=headers)
            if r.status_code == 200:
                print("  ✓ OpenWA Gateway is ONLINE & AUTHENTICATED.")
                sessions = r.json()
            else:
                print(f"  ✗ Auth check failed (HTTP {r.status_code}): {r.text}")
                return False
        except Exception as e:
            print(f"  ✗ Failed to connect to OpenWA at {api_base}: {e}")
            return False

        # 2. Resolve or Create Session
        print(f"\n[STEP 2/4] Resolving session '{session_name}'...")
        session_id = None
        for s in sessions:
            if s.get("name") == session_name:
                session_id = s.get("id")
                print(f"  ✓ Found existing session '{session_name}' (ID: {session_id}, Status: {s.get('status')})")
                break

        if not session_id:
            create_resp = client.post(f"{api_base}/sessions", headers=headers, json={"name": session_name})
            if create_resp.status_code == 201:
                session_obj = create_resp.json()
                session_id = session_obj["id"]
                print(f"  ✓ Created new session '{session_name}' (ID: {session_id})")
            else:
                print(f"  ✗ Failed to create session: {create_resp.status_code} {create_resp.text}")
                return False

        # 3. Start Session & Fetch QR Code
        print(f"\n[STEP 3/4] Fetching pairing QR code for session '{session_name}'...")
        try:
            client.post(f"{api_base}/sessions/{session_id}/start", headers=headers, timeout=5.0)
        except Exception:
            pass  # Background start may hold request

        # Poll QR code
        qr_saved = False
        for attempt in range(1, 10):
            try:
                qr_resp = client.get(f"{api_base}/sessions/{session_id}/qr", headers=headers)
                if qr_resp.status_code == 200:
                    data = qr_resp.json()
                    qr_data_url = data.get("qrCode", "")
                    if qr_data_url.startswith("data:image/png;base64,"):
                        b64_str = qr_data_url.replace("data:image/png;base64,", "")
                        qr_path = Path(__file__).resolve().parent.parent / "qr_code.png"
                        qr_path.write_bytes(base64.b64decode(b64_str))
                        print("\n" + "═" * 70)
                        print("📲 QR CODE READY TO SCAN!")
                        print(f"   • Saved image to: {qr_path}")
                        print(f"   • Or open web dashboard at: {base_url}")
                        print("   • Steps: WhatsApp on phone ➔ Linked Devices ➔ Link a Device ➔ Scan QR")
                        print("═" * 70 + "\n")
                        qr_saved = True
                        break
            except Exception as err:
                time.sleep(2)
            time.sleep(2)

        if not qr_saved:
            print(f"  ℹ️ Session engine active. Visit {base_url} to view QR and status.")

        # 4. Register Inbound Webhook
        print(f"\n[STEP 4/4] Registering inbound webhook at {webhook_url}...")
        try:
            hook_payload = {
                "url": webhook_url,
                "events": ["message.received", "session.status"],
                "secret": settings.OPENWA_WEBHOOK_SECRET,
            }
            hook_resp = client.post(f"{api_base}/webhooks", headers=headers, json=hook_payload)
            if hook_resp.status_code in (200, 201):
                print("  ✓ Inbound webhook registered successfully.")
            else:
                print(f"  ℹ️ Webhook registration note: HTTP {hook_resp.status_code}")
        except Exception as he:
            print(f"  ! Webhook registration: {he}")

    print("\n" + "=" * 70)
    print("🎯 SETUP COMPLETE! Scan the QR code with your phone to start receiving live alerts.")
    print("=" * 70)
    return True


if __name__ == "__main__":
    setup_openwa()
