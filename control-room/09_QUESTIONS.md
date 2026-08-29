# RailTwin-X — Open Questions & Decision Requests (09_QUESTIONS.md)

**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Audit Date:** 2026-08-28  

The following 4 architectural decisions and operational choices could not be resolved purely from static code analysis and require input from the human engineering lead:

---

### Q1: Platform Re-Optimizer Interlock Integration (Risk SF-03)
- **Context:** Currently, `api/brain.py` applies the 5-rule safety interlock to individual train delay advisories, but `POST /stations/{code}/reoptimize` returns re-optimized platform assignments directly from `engine/ops.py` without piping each adjusted train schedule through `safety/interlock.py`.
- **Question:** Should we make `MasterSafetyInterlock.verify_and_guard()` a mandatory blocking gate on all re-optimized platform swaps, or should unphysical schedule shifts be displayed as warnings in the Next.js cockpit with an operator override?
- **Recommendation:** Mandatory blocking gate (Task `TSK-SF-01`).

---

### Q2: Automated Action on PSI Drift Threshold Breach (Risk ML-03)
- **Context:** `ml/drift.py` successfully calculates feature PSI and classifies distributions as GREEN, AMBER, or RED. However, when RED ($	ext{PSI} \ge 0.25$) is reached, it only logs an alert to stdout without modifying system behavior.
- **Question:** When PSI reaches RED, should the backend:
  1. Automatically widen CQR conformal uncertainty bands $\hat{Q}$ by $+50\%$ dynamically, OR
  2. Automatically fall back to the Linear Regression benchmark model (B3), OR
  3. Trigger an asynchronous background retraining job via `scripts/nightly_pipeline.py`?
- **Recommendation:** Option 1 (widen CQR bounds immediately) + Option 3 (trigger retraining).

---

### Q3: SQLite Database Event Retention & Archival TTL (Risk DA-04)
- **Context:** `station_events` and `sim_ledger` currently store 33,600+ events and grow with every collector cycle. Without a pruning policy, the SQLite database file will experience unbounded growth.
- **Question:** What is the preferred historical data retention window before archival?
  - 30 days active rolling window in SQLite + cold Parquet export in `data/cache/`?
  - 90 days active rolling window?
- **Recommendation:** 30 days active rolling window in SQLite with automated Parquet export during nightly pipeline.

---

### Q4: WhatsApp Gateway Deployment Mode (OpenWA vs Meta Cloud API)
- **Context:** `notifications/` currently defaults to self-hosted OpenWA on `localhost:2785`, with documented upgrade architecture in `docs/upgrade-to-meta-cloud.md`.
- **Question:** For production staging, should we continue using the zero-cost self-hosted OpenWA Chromium sidecar with local SMS fallback, or immediately provision the official Meta WhatsApp Cloud API credentials?
- **Recommendation:** Retain OpenWA + Mock/MSG91 SMS for dev/demo; enable Meta Cloud API adapter via `WHATSAPP_PROVIDER=meta` in production.

---

AUDIT_BASELINE: d074cc69188948644de72cad7bd4a248547e26ac | 2026-08-28 | audit-v2.0
