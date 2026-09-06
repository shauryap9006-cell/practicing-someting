# 📄 PRD — RailTwin-X (Compact Definitive Edition)

**SIH 2026 · PS 26028 · Dynamic ETA Forecast for Coaching & Freight Trains · v4.0 · SCOPE-FROZEN**

---

## 1. Product Statement

**RailTwin-X** is a real-time railway **delay intelligence engine**: it predicts train
arrivals with calibrated confidence bands, explains every delayed minute exactly,
simulates how delays cascade across the network, and repairs broken platform plans in
one click. Built for **station masters, section controllers, and control-room staff** — the users the PS
names but consumer apps ignore — and exposed to external applications via a high-performance REST API.

**Identity line:** *The prediction engine Railways' own apps and control rooms should be drinking from.*

**Core problem being solved:** Legacy formula `ETA = schedule + current delay − assumed recovery`
assumes deterministic recovery, treats trains in isolation, and states guesses with
total confidence. Cascades (crossings, late rakes, single-line meets, freight congestion) arrive as surprises.

---

## 2. Users (priority order)

| # | User | Job-to-be-done | Features serving them |
|---|---|---|---|
| P1 | Station Master | Repair platform plan before reality arrives | F8, F9 |
| P2 | Section Controller | See the cascade 3 hours early; manage DFC freight/passenger precedence | F6, F7, F10 |
| P3 | Crew Controller | Duty-breach early warning | F13 |
| P4 | Cleaning/Catering | Realistic turnaround windows | F8 alerts |
| P5 | Passenger / Freight Planner *(indirect, via API)* | Honest ETA band + explainable root cause | F2–F5, F12, API |
| P6 | Developer/Integrator | Stable OpenAPI contracts with sub-100ms response time | F11 |

**Anti-persona:** NOT a signaling system, NOT autonomous actuation. Advisory-only, labeled on every screen (`human_ack_required: true`).

---

## 3. The 14 Features (THE SCOPE LAW — nothing else gets built)

| ID | Feature | Acceptance (pass/fail) | Pri |
|---|---|---|---|
| F1 | Live train state | Position/delay/next-station ≤5s after event | 🔴 |
| F2 | ETA all upcoming stations | Every station, updated ≤5s on state change | 🔴 |
| F3 | Confidence band | calibrated $p_{10}, p_{50}, p_{90}$ on every ETA; band widens with horizon | 🔴 |
| F4 | Journey timeline | Per-station sched vs predicted with status color encoding | 🔴 |
| F5 | Delay autopsy | Cause minutes sum EXACTLY to total (automated ledger balance) | 🔴 |
| F6 | Cascade view | ≥3 trains inherit on injection, each with causal tag | 🔴 |
| F7 | Same-rake tracker | Outgoing delay = f(incoming actual + turnaround); NTES-comparison card | 🔴 |
| F8 | Platform Gantt + conflicts | Red overlap detection ≤5s after ETA shift | 🔴 |
| F9 | One-click re-optimize | Conflict-free plan <2s + "N swaps resolved M conflicts" + rollback | 🔴 |
| F10 | Corridor schematic | Trains colored green/amber/red by predicted band | 🔴 |
| F11 | REST API | 10 endpoints, stable contracts, Swagger docs, HTTP polling + TTL cache | 🟡 |
| F12 | Station display widget | Next 5 arrivals + bands, 3m readable | 🟡 |
| F13 | Crew duty alert | Projected breach time + relief station, ADVISORY label | 🟡 |
| F14 | **Proof table** | MAE/hit-rate/coverage vs baselines B1+B2 on held-out real week | 🔴 **wins** |

**Freight & DFC Extension**: Incorporates Dedicated Freight Corridor (DFC) operations, managing priority-4 freight movement, siding loop holding rules, and mixed passenger-freight dispatching.

**Banned forever:** Kafka · K8s · Neo4j/PostGIS · GNN/TFT · Unmanaged WebSockets (HTTP polling with 5-sec client TTL caching used) ·
mobile app · OR-Tools · any 15th feature. New ideas → roadmap slide, not code.

---

## 4. Machine Learning & Safety Architecture

- **Champion Model**: PyTorch **2-Layer GRU (Gated Recurrent Unit)** neural network capturing sequential spatial-temporal propagation across route stops.
- **Quantile Estimators**: **LightGBM Quantile Gradient Boosted Trees** ($p_{10}, p_{50}, p_{90}$) trained under pinball loss with conformalized quantile regression (CQR) calibration.
- **23 Leakage-Safe Features**: Static train/route traits, temporal schedule embeddings, dynamic delay velocity/acceleration, weather parameters (fog/rain/temp), and network spatial track graph topology features (`trains_ahead_30k`, `trains_behind_30k`, `opposing_trains_30k`, `min_predicted_headway_next_station`, `sum_delay_trains_ahead_30k`, `section_occupancy_pct`).
- **Deterministic Safety Interlock Layer**: 5 pure deterministic kinematic rules (Input Sanity, Quantile Monotonicity, Priority Recovery Limits, Absolute Operational Bounds, Monotonic Horizon Drift).
- **Roadmap Blueprint**: High-frequency multi-sensor track-level fusion (EKF, IMM, HMM, MHT) preserved in `docs/v4_architecture/` for direct ISRO RTIS locomotive OBU integration.

---

## 5. Success Metrics (measured on real held-out data, published honestly)

| ID | Metric | Target |
|---|---|---|
| SM1 | MAE @1h vs baseline B2 (official-style) | **≥25% lower** |
| SM2 | ±10-min hit rate @1h | ≥60% |
| SM3 | Conformal 80% band coverage | 75–85% |
| SM4 | Ledger exactness | 100% of rows balance |
| SM5 | Cascade demo | ≥3 correct inheritances, every rehearsal |
| SM6 | Re-optimize | resolves all injected conflicts <2s |
| SM9 | Real data corpus | ≥50,000 station events |

---

## 6. Stack & Data (locked)

**Stack:** PyTorch · LightGBM · SimPy · networkx · pandas · scikit-learn · FastAPI · Open-Meteo · Next.js · recharts · SQLite.

**Data:** 150 daily trains (passenger + DFC freight), Northern Railway corridor (NDLS-CNB-DDU), 3-adapter fallback chain (RapidAPI → Live Scrape → Deterministic Mock Replay), idempotent SQLite storage with quality gates.
