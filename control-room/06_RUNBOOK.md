# RailTwin-X — Standard Runbook (06_RUNBOOK.md)

**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Audit Date:** 2026-08-28  

---

## 1. Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed database (mixed passenger + DFC network)
python -m data.seed --network=mixed

# 3. Run full test suite (93 tests)
pytest tests/ -v

# 4. Start backend API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start frontend Next.js cockpit (in /web)
cd web && npm install && npm run dev
```

## 2. Nightly ML Retraining & Calibration

```bash
# Full nightly pipeline: seed -> train LightGBM -> train GRU -> evaluate -> check drift
python -m scripts.nightly_pipeline --network=mixed
```

## 3. Emergency Failover & Recovery
- **OpenWA Gateway Outage:** System automatically routes alerts through `SMSChannel`. Verify SMS gateway keys in `.env` (`SMS_PROVIDER=msg91` or `fast2sms`).
- **Database Corruption / Reset:** Run `rm data/railtwin.db && python -m data.seed --network=mixed` to restore canonical baseline state in < 5 seconds.

---

AUDIT_BASELINE: d074cc69188948644de72cad7bd4a248547e26ac | 2026-08-28 | audit-v2.0
