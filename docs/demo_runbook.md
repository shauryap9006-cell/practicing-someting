# RailTwin-X v4 — Demo Runbook

> **For:** SIH 2026 Demo / Evaluation Session  
> **Duration:** ~12 minutes end-to-end  
> **Prerequisites:** Python environment with dependencies installed; DB seeded; models trained

---

## Pre-Demo Checklist (15 min before)

```bash
# 1. Reseed database with mixed network (passenger + DFC freight)
make seed-mixed

# 2. Verify 78/78 tests green
make test

# 3. Start API server
make api
# → Server at http://localhost:8000   Swagger at http://localhost:8000/docs

# 4. Open browser tabs:
#    - http://localhost:8000/docs           (Swagger UI)
#    - http://localhost:8000/v1/health      (health check)
```

---

## Demo Script

### Step 1 — System Health (30 sec)

```
GET /v1/health
```
**Show:** `"status": "healthy"`, DB connected with 33,600 events, models loaded.

**Say:** *"RailTwin-X has 150 trains, 110 stations including DFC corridor, 33,600 historical events for ML training."*

---

### Step 2 — Live ETA with Confidence Band (2 min)

```
GET /v1/trains/12034/eta?station=NDLS
```
**Show:** `predicted_arr`, `confidence_band` with p10/p50/p90, `tier_used: Tier2_LightGBM_CQR`

**Say:** *"Unlike a single number, we give a calibrated confidence band. The p90 worst case is our safety margin — dispatchers act on this, not the optimistic p10."*

**Then show journey timeline:**
```
GET /v1/trains/12034/journey
```
*"Every stop ahead has its own prediction. Green/amber/red color coding makes it instantly scannable."*

---

### Step 3 — Delay Autopsy (Causal Explainability) (1.5 min)

```
POST /v1/simulate  (inject 45-min delay at CNB for train 12034)
GET  /v1/trains/12034/autopsy
```
**Show:** Exact breakdown: `CROSSING_HOLD: 18m`, `PLATFORM_WAIT: 12m`, `EXT_DWELL: 15m`

**Say:** *"Every delay minute is causally attributed. This is exact accounting — the minutes sum to 45 exactly. No ML black box — pure deterministic discrete-event simulation."*

---

### Step 4 — DFC Freight Corridor (1.5 min)

```
GET /v1/meta/trains   (show freight trains 90001–90030)
GET /v1/trains/90001/eta?station=JNPT
GET /v1/conflicts/90001
```
**Show:** Conflict scan showing 14-minute headway enforcement for coal_rake trains.

**Say:** *"India's Dedicated Freight Corridors run at 100 km/h with 3,000-tonne loads. Coal rakes need 14 minutes headway vs 5 minutes for passenger — we enforce this in the deterministic safety layer, not in ML."*

---

### Step 5 — Dispatcher Advisory + ACK (1.5 min)

```
POST /v1/advise   {"train_no": "12034", "target_station": "CNB"}
```
**Show:** Full advisory with `suggested_action`, `human_ack_required: true`, `conflicts` array.

**Then ACK it:**
```
POST /v1/advise/{adv_id}/ack   {"decision": "accepted", "dispatcher_id": "DISP-42"}
```
**Say:** *"Every advisory requires explicit dispatcher sign-off. The audit trail is stored in the database — regulators can query every decision ever made."*

---

### Step 6 — Network State + Conflict Scan (1 min)

```
GET /v1/network/state
GET /v1/conflicts/12034
```
**Show:** Network overview with 150 active trains; conflict scan identifying STATION_HEADWAY and SINGLE_LINE_OPPOSING risks.

---

### Step 7 — ML Metrics Proof Table (1 min)

```
GET /v1/evaluation/summary
```
**Show:** F14 proof table:
- 1h: **7.4 min MAE** (−26% vs Baseline-2, −19% vs Baseline-3)
- 3h: **12.2 min MAE** (−52% vs Baseline-2)
- 6h: **17.2 min MAE** (−65% vs Baseline-2)
- Coverage: 81–99% across horizons

**Say:** *"These are held-out test week numbers — not training scores. The Wilcoxon test confirms our GRU champion is statistically significantly better than the LightGBM challenger."*

---

### Step 8 — PSI Drift Monitor (45 sec)

```bash
make drift
```
**Show:** 7 features, all GREEN (PSI < 0.10), report saved to `artifacts/drift_report.json`.

**Say:** *"In production, this runs every night. If PSI goes RED, it triggers automatic retraining."*

---

## If Something Goes Wrong

| Symptom | Fix |
|---|---|
| `404 TRAIN_NOT_FOUND` for `12034` | Run `make seed-mixed` then restart |
| `500 ETA_PREDICTION_ERROR` | Run `make train eval` first |
| `models: pending_training` in health | Run `make train eval` |
| Port 8000 in use | Kill existing process; `make api` |

---

## Key Numbers to Remember

- **Test MAE:** 7.4 / 12.2 / 17.2 min (1h/3h/6h)
- **vs Baseline-2:** −26% / −52% / −65%
- **80% Coverage:** 81.1% / 82.5% / 99.5%
- **Quantile crossing violations:** 0
- **Test suite:** 78/78 green
- **Trains:** 150 (120 passenger + 30 DFC freight)
- **Stations:** 110 (100 passenger + 10 DFC)
