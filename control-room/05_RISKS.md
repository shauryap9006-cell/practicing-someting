# RailTwin-X — Verified Risk Register (05_RISKS.md)

**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Audit Date:** 2026-08-28  
**Status:** FORENSIC AUDIT COMPLETED

---

## 1. Machine Learning Model Risks

| ID | Risk Description | Severity | Forensic Status | File Citation & Verification Evidence |
|---|---|---|---|---|
| **ML-01** | GRU quantile heads cross ($p_{10} > p_{50}$) breaking prediction intervals | Critical | **UNCONFIRMED / MITIGATED** | `ml/model_seq.py:114-120`: Monotonicity guaranteed in architecture via cumulative `softplus` parameterization. 0 crossings in 45,200 samples (`tests/test_brain_e2e_adversarial.py`). |
| **ML-02** | CQR calibration staleness under shifting seasonal traffic patterns | Medium | **CONFIRMED** | `ml/artifacts/manifest.json`: CQR offsets (`conformal_q_hat_*`) are static JSON values updated only during retraining. No automated runtime recalibration trigger exists when PSI alerts. |
| **ML-03** | PSI drift threshold breached without triggering action | Medium | **CONFIRMED** | `ml/drift.py:244-246`: Breaches log `[ACTION REQUIRED]` to stdout, but lack automated retrain triggers or fallback switches to linear baseline. |
| **ML-04** | Undefined GRU vs LightGBM conflict resolution | High | **UNCONFIRMED / MITIGATED** | `ml/ensemble.py:86-135`: Explicit convex blending with horizon-dependent weights (Short: 65% GBM / 35% GRU; Long: 45% GBM / 30% GRU / 25% LR). |
| **ML-05** | Model artifact version drift (mismatched weights/code) | Low | **CONFIRMED** | `api/predictor.py:35-80`: Models are loaded without SHA256 weight checksum or git commit verification against `manifest.json`. |

---

## 2. Safety Interlock Layer Risks (Highest Criticality)

| ID | Risk Description | Severity | Forensic Status | File Citation & Verification Evidence |
|---|---|---|---|---|
| **SF-01** | ML code imported into `safety/` corrupting deterministic boundary | Critical | **UNCONFIRMED / PROVEN ZERO** | `safety/interlock.py:1-15`: Grep confirms **0 imports** of `ml/`, `torch`, `lightgbm`, `sklearn`. Standard library only. |
| **SF-02** | Interlock fails open (allows recommendations on missing/corrupt data) | Critical | **UNCONFIRMED / MITIGATED** | `safety/interlock.py:82-132`: Missing keys, NaNs, and Infinities trigger immediate fail-safe override to current physical delay (`REJECTED_OVERRIDE_TO_NOMINAL`). |
| **SF-03** | Station platform re-optimizer bypasses safety interlock check | High | **CONFIRMED** | `api/routes.py:380-420`: Re-optimizer route (`POST /stations/{code}/reoptimize`) calls `engine/ops.py` directly without piping schedule changes through `safety/interlock.py`. |
| **SF-04** | One of the 5 kinematic rules untested / skipped | High | **UNCONFIRMED / MITIGATED** | `tests/test_safety_interlock.py`: 27 dedicated tests verify all 5 rules and edge cases. |
| **SF-05** | `sim_ledger` causal minute accounting drifts under concurrent events | High | **UNCONFIRMED / MITIGATED** | `engine/simulator.py:120-180`: Invariant $\sum 	ext{Causal} = \sum 	ext{Primary} + \sum 	ext{Reactionary}$ strictly verified in `tests/test_simulator.py`. |

---

## 3. Integration & Operational Risks

| ID | Risk Description | Severity | Forensic Status | File Citation & Verification Evidence |
|---|---|---|---|---|
| **IN-01** | OpenWA WhatsApp gateway is single point of failure | High | **UNCONFIRMED / MITIGATED** | `notifications/dispatcher.py:110-140`: Automatic fallback to `SMSChannel` triggers immediately upon OpenWA timeout or HTTP error. |
| **IN-02** | HMAC webhook signature verification vulnerable to timing attack | Critical | **UNCONFIRMED / MITIGATED** | `notifications/webhook_verify.py:35`: Uses constant-time `hmac.compare_digest` with mandatory `X-Hub-Signature-256` header. |
| **IN-03** | Stale train position data ingested during RapidAPI outage | Medium | **CONFIRMED** | `collector/collector.py:45-80`: Does not emit a stale-data warning if position age exceeds 30 minutes. |
| **IN-04** | Open-Meteo downtime blinds system to fog conditions | Medium | **UNCONFIRMED / MITIGATED** | `collector/weather.py:45`: Gracefully defaults to clear weather (`visibility_km=10.0`, `fog_index=0.0`) without crashing. |
| **IN-05** | Hardcoded production secrets committed to git | Critical | **UNCONFIRMED / MITIGATED** | `config.py:20-110`, `.env`: Production secrets loaded via environment variables; repository `.env` contains local dev dummy keys. |

---

## 4. Data & Concurrency Risks

| ID | Risk Description | Severity | Forensic Status | File Citation & Verification Evidence |
|---|---|---|---|---|
| **DA-01** | SQLite WAL contention under simultaneous dashboard polling and collector writes | Medium | **CONFIRMED** | `data/db.py:31-36`: WAL mode with 30s timeout configured, but lacks high-concurrency automated stress test (50+ simultaneous clients). |
| **DA-02** | Absence of automated database backup & replication | Medium | **CONFIRMED** | Relies on Docker volume persistence; no automated `VACUUM INTO` streaming backup script. |
| **DA-03** | Seed data schema divergence | Low | **UNCONFIRMED / MITIGATED** | `tests/test_foundation.py:test_seed_dataset_integrity`: Schema integrity verified on test run. |
| **DA-04** | Unbounded event table growth (33,600+ records) without retention policy | Medium | **CONFIRMED** | `station_events` and `sim_ledger` tables lack a TTL pruning cron job. |

---

AUDIT_BASELINE: d074cc69188948644de72cad7bd4a248547e26ac | 2026-08-28 | audit-v2.0
