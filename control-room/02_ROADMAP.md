# RailTwin-X — Strategic Roadmap (02_ROADMAP.md)

**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Audit Date:** 2026-08-28  

---

## Milestone 1: Safety & Re-Optimizer Hardening (Target: Sprint 1)
- **Goal:** Close all safety interlock routing gaps and establish automated database concurrency validation.
- **Success Criteria:**
  - 100% of re-optimized schedules verified by `MasterSafetyInterlock` (`TSK-SF-01`).
  - SQLite WAL concurrency stress test passing with 50 simultaneous clients (`TSK-DA-01`).
  - SHA256 model checksum verification at startup (`TSK-ML-01`).

## Milestone 2: Dynamic Calibration & Auto-Healing ML (Target: Sprint 2)
- **Goal:** Autonomous feature drift handling and dynamic conformal interval adjustment.
- **Success Criteria:**
  - Automated CQR band widening upon PSI RED drift detection (`TSK-ML-02`).
  - Automated SQLite event pruning and non-blocking `VACUUM INTO` backup (`TSK-DA-02`).
  - Stale train telemetry age warning headers emitted by collector (`TSK-IN-01`).

## Milestone 3: Enterprise Cloud Notifications & Sensor Fusion (Target: Sprint 3)
- **Goal:** Production multi-channel alerting and v4 ISRO RTIS GPS sensor fusion.
- **Success Criteria:**
  - Meta WhatsApp Cloud API adapter implemented (`TSK-IN-02`).
  - SimPy pre-check gate integrated into station-master cockpit (`TSK-OP-01`).

---

AUDIT_BASELINE: d074cc69188948644de72cad7bd4a248547e26ac | 2026-08-28 | audit-v2.0
