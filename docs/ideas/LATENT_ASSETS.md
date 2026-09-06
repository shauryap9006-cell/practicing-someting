# PHASE 0 — LATENT ASSET INVENTORY
**RailTwin-X · SIH PS 26028 · Dynamic ETA Forecasting**

> **UPDATED 2026-09-05 after commit `f371ecb` (+ working tree):** Assets #2 (cascade sim → ripple DSS), #8 (rake doom), #9 (connection custody), #15/#17 (model performance benchmarks), #19/#20 (shadow/advisory analytics) now have LIVE surfaces (`api/demo_routes.py`, `RippleBoardPage`, `HonestModelCardPage`, `ForesightConsolePage`). They are marked **[LIVE]** below. The ledger scoreboard (#1, #7) still has **zero UI consumers** — now the highest-value remaining asset. Status markers: **[DEAD]** (unchanged), **[LIVE]** (surfaced in f371ecb), **[HALF]** (backend surfaced, passenger surface missing).

---

## 0.1 DEAD CAPABILITY — Built but never surfaced

| # | Capability | File:Line | Current Consumers | Possible Surfaces |
|---|---|---|---|---|
| 1 | **[DEAD — top remaining asset]** **Prediction Ledger Scoreboard** — `get_calibration_scoreboard()` returns live MAE, Winkler, coverage, chain integrity. API route exists (`api/routes.py:874`) but **zero UI consumers**. | `engine/prediction_ledger.py:187` | Graded by `live_tracker.py:322`; receipts recorded by comparator (`api/demo_routes.py:247`). Scoreboard return value never rendered. | Live ledger card on ForesightConsole / model-card page. ~2–3h. |
| 2 | **[LIVE — partial]** **CascadeSimulator + ripple DSS** — `/v1/cascade/ripple` (`api/demo_routes.py:352+`) now surfaces rake turnaround deficits + hold advisories via `RippleBoardPage`. The full SimPy what-if A/B (with/without intervention diff) remains narrative. | `engine/simulator.py:57` | `RippleBoardPage` (rake + connection half), `/v1/simulate/what-if` (raw). | Full counterfactual lab = super-bet narrative. |
| 3 | **ConformalPIDController** — Streaming PID controller for coverage calibration, persisted in SQLite. Never displayed to any user. | `ml/conformal.py:311` | Only in memory during prediction calls. State stored but never read. | Regime awareness dashboard: "current α=0.23, coverage trending to 82%" |
| 4 | **PSIDriftMonitor** — Computes PSI per feature between training and live windows. Runs as CLI (`python -m ml.drift`) but output never reaches API or UI. | `ml/drift.py:179` | Nightly MLOps pipeline (if wired). Output saved to `drift_report.json`. | Drift badge on model info endpoint, "REGIME: FOG SEASON" indicator |
| 5 | **CUSUMDetector & ADWINDetector** — Online change-point detectors for regime shifts. Exist in `ml/drift.py:73` but never invoked in live serving. | `ml/drift.py:73,98` | None — dead code path. | Anomaly early-warning: "delay velocity shifted at 06:45 — possible signal failure upstream" |
| 6 | **AdaptiveConformalInference** — Gibbs & Candès 2021 ACI for streaming alpha updates. Never wired into serving. | `ml/conformal.py:216` | None. | Real-time coverage tracker showing α_t evolution |
| 7 **D5** | **[DEAD]** **verify_chain_integrity()** — Verifies SHA-256 hash chain. Route `/ledger/verify` exists (`api/routes.py:886`) — never called from UI. | `engine/prediction_ledger.py:159` | `get_calibration_scoreboard()` internally. | "✓ Chain intact" verification button — pair with #1. |
| 8 **D4** | **[LIVE — controller half]** **RakeResolver doom logic** — now surfaced as turnaround buffer deficits + CRITICAL_DEFICIT status in `/v1/cascade/ripple` + `RippleBoardPage`. **Passenger doom card still missing.** | `engine/rakes.py:57` (superseded by `api/demo_routes.py:352` logic) | `RippleBoardPage` (controllers). | Passenger-facing doom card on PassengerTrackerPage (~1–2h). |
| 9 **D4** | **[LIVE]** **ConnectionCustodyEngine** — now surfaced via `/v1/cascade/ripple` → `top_hold_advisories` with net passenger-hours, on `RippleBoardPage` with ADVISORY-ONLY jurisdiction framing. | `engine/ops.py:459` | `api/demo_routes.py:412` → `RippleBoardPage`. | Done. Possible upgrade: per-train connection chips in tracker. |
| 10 | **CrewDutyEngine** — Projects crew duty breaches. `CrewAlert` dataclass exists. Never dispatched to UI. | `engine/ops.py:341` | `api/workforce_routes.py` (if wired). | Crew fatigue dashboard: "Crew C-412 on Train 12556: projected breach in 2h 10m" |
| 11 | **ConflictScanner** — Detects station headway, single-line opposing, and catchup conflicts. Produces `ConflictRecord` objects. Only dispatches via notification (no persistent API). | `engine/conflicts.py:76` | `api/brain.py` (if wired). | Conflict heat map on corridor schematic — "S1 CNB-DDU: HIGH conflict density zone" |
| 12 | **Signal-hold inference** — `inferred_signal_aspect` (RED/YELLOW/DOUBLE_YELLOW/GREEN) computed per train per tick. Exists in `LiveTrainPosition` but not exposed in API response. | `engine/live_tracker.py:516` | `_track_single_train_with_event()` only. | Signal aspect overlay on live map: trains colored by inferred block state |
| 13 | **PositionResolver** — Bayesian posterior over train's possible km positions. `top_k(3)` returns marginalized positions with probabilities. Never exposed. | `engine/position_resolver.py` | `api/predictor.py:401`. | "Train location confidence: 78% — most likely km 342, but 15% chance still at km 290" |
| 14 | **[DEAD — slate medium]** **DaySpatialIndex** — Minute-resolution numpy grid of every train's km position for a day. 1440×N array. Still feeds only ML features. | `engine/spatial_context.py:152` | `SnapshotGenerator` for ML features. | 6-hour congestion radar — the medium on the build slate. |
| 15 | **EnsemblePredictor — NNLS weights by horizon** — `fit_stacking_weights()` produces per-bucket weights (gbm, gru, lr, B1_frozen, B3_linear). Stored in `registry.json`. Never shown. | `ml/ensemble.py:30` | Nightly training pipeline. | "At 6-hour horizon: 35% LightGBM + 15% GRU + 35% Linear Regression" |
| 16 | **Top-3 feature drivers** — `_extract_top_drivers()` returns per-prediction delay driver attribution. Exists in `PredictorService` but returns heuristic defaults when `df_feat=None`. | `api/predictor.py:474` | `predict_train_eta()` for response formatting. | Driver bar chart in train detail panel |
| 17 | **Stacking weights by horizon** — Short/medium/long horizon weights stored in manifest. Never surfaced in UI or API. | `ml/train.py:299` | Training pipeline. | Horizon-adaptive prediction quality indicator |
| 18 | **Shadow log** — `shadow_log` table records champion vs challenger delta per prediction. Never queried for display. | `api/predictor.py:83` | `_ensure_shadow_log_table()` creates it. | "Shadow evaluation: GRU vs GBM delta avg 2.3 min" |
| 19 | **NormalizedCQR** — `ml/conformal.py:254` — heteroskedasticity-aware CQR. Never invoked. | `ml/conformal.py:254` | None. | Wider bands for high-uncertainty routes |
| 20 | **Brain advisory audit** — `brain_advisory_audit` table logs inputs, outputs, conflicts. Never queried for analytics. | `data/schema.sql:155` | `api/brain.py`. | Advisory acceptance rate: "47 of 312 brain advisories accepted" |
| 21 | **[NEW in f371ecb]** **Performance benchmarks / honest horizon cards** — `/v1/model/performance` (`api/routes.py:66`) reads `metrics.json` dynamically (honest 1h tie, −36.3% 3h, −51.7% 6h vs B2). | `api/routes.py:66` → `ml/artifacts/metrics.json` | `HonestModelCardPage`, `ForesightConsolePage`. **LIVE** — keep `metrics.json` current. |
| 22 | **[NEW in f371ecb]** **Shock injection DSS** — `/v1/demo/inject-event` + comparator cone reaction. In-memory `_ACTIVE_SHOCKS` (`api/demo_routes.py:30`) — resets on restart. | `api/demo_routes.py:44` | `ComparatorPage`, `ForesightConsolePage`. | LIVE. Don't claim persistence. |

---

## 0.2 DEAD DATA — Collected but never productized

| # | Dataset | Location | Volume | Product Possibility |
|---|---|---|---|---|
| 21 | **station_events** — collected delay events | `data/station_events` | ~300k+ rows | Historical search: "why was my train late last Tuesday?" |
| 22 | **weather** + **weather_hourly** — fog_flag, precip, humidity, visibility | `data/weather` | 350k+ records | Fog season index, "today's corridor visibility map" |
| 23 | **live_delay_ledger** — exact causal delay ledger events | `data/live_delay_ledger` | Ongoing append | Causal delay analytics dashboard — "today: 73% signal holds, 12% weather" |
| 24 | **sim_ledger** — simulated cascade events | `data/sim_ledger` | Per sim run | Scenario comparison: "without TSR at km 200, 8 fewer delay-minutes cascaded" |
| 25 | **eta_prediction_ledger** — hash-chained predictions | `data/eta_prediction_ledger` | Ongoing | Public accountability scoreboard (D5) |
| 26 | **conformal_pid_state** — streaming alpha evolution | `data/conformal_pid_state` | Per group key | Regime tracker: "α has drifted from 0.20 → 0.27 over past 3 days" |
| 27 | **drift_report.json** — PSI per feature | `ml/artifacts/drift_report.json` | Daily | Drift alert feed: "feature `current_delay` PSI=0.31 — RED" |
| 28 | **OSM corridor geometry** — section polylines | `engine/track_graph.py` | 785km corridor | Animated corridor with section-occupancy heatmap |
| 29 | **rake_links** — same-rake pairs | `data/rake_links` | ~30 links | Rake doom timeline widget |
| 30 | **speed_restrictions** — active TSRs | `data/speed_restrictions` | Ongoing | TSR impact heatmap: "active TSR between CNB-PRYJ costs avg +8 min" |
| 31 | **manifest.json + registry.json** — model weights, q_hats, stacking | `ml/artifacts/` | Per training run | Model transparency card: "current model: LightGBM, q_hat=2.3, trained on 18 months data" |
| 32 | **shadow_log** — champion vs challenger delta | `data/shadow_log` | Per prediction | Shadow evaluation leaderboard |
| 33 | **brain_advisory_audit** — advisory inputs/outputs | `data/brain_advisory_audit` | Per advisory | Brain acceptance funnel |
| 34 | **ad_events** — human-confirmed set-in/set-out | `data/ad_events` | Ongoing | Prediction vs human-confirmed discrepancy analytics |
| 35 | **notification_log** — outbound alert outcomes | `data/notification_log` | Ongoing | Alert effectiveness: "High-severity conflict alerts: 73% acknowledged within 5 min" |

---

## 0.3 DEAD SIGNAL — Computed and discarded

| # | Signal | Computed In | Discarded At | Product Surface |
|---|---|---|---|---|
| 36 | **Winkler interval score** per prediction | `ml/conformal.py:46` | Never stored or surfaced | "Sharpness score" badge per prediction |
| 37 | **CRPS** per prediction | `ml/conformal.py:69` | Never stored | Aggregate CRPS on scoreboard |
| 38 | **Confidence halo (exponential decay)** | `engine/live_tracker.py:433` | Only `LiveTrainPosition.confidence` stored — not the decay curve | "Staleness indicator" on position map |
| 39 | **Position entropy** | `engine/position_resolver.py` | Only `position_belief_entropy` as ML feature | "Location certainty: HIGH/MEDIUM/LOW" badge |
| 40 | **Trains ahead/behind/opposing in 30km** | `engine/spatial_context.py:176` | Only used as ML features | Congestion index per section |
| 41 **D2** | **Section occupancy %** | `engine/spatial_context.py:209` | Only used as ML feature | Real-time corridor congestion radar |
| 42 | **Posterior probabilities** (top-3 candidate positions) | `engine/position_resolver.py` | Only top-1 used in serving | "Possible locations" chips on train detail |
| 43 | **Hop-level delta prediction** vs **direct prediction** | `api/predictor.py:282` | Only blended result returned | "Uncertainty increases after hop 3" indicator |
| 44 | **Mondrian CQR q_hats by horizon** (1h/3h/6h) | `ml/conformal.py:96` | Only global q_hat used | Horizon-specific uncertainty badges |
| 45 | **Winkler score per ledger row** | `engine/prediction_ledger.py:145` | Stored in DB but never aggregated for API | Per-cause-type Winkler breakdown |
| 46 | **NNLS stacking weights by horizon** | `ml/ensemble.py:30` | Stored in manifest.json | "Model blend at long range" transparency |
| 47 | **Effective sample size (ESS)** | `ml/train.py:84` | Printed to console only | "ESS=44,200 — model trained on 18 months" |
| 48 | **Drift PSI per feature** | `ml/drift.py:34` | Saved to JSON, never surfaced | Feature-level drift feed |
| 49 | **CUSUM change points** | `ml/drift.py:73` | Never triggered or stored | Change-point alert feed |
| 50 | **ADWIN drift flag** | `ml/drift.py:98` | Never triggered or stored | Regime change detection |
| 51 | **Signal aspect inference** (RED/YELLOW/GREEN) | `engine/live_tracker.py:518` | Exists in position object, never in API response | Signal overlay on map |
| 52 | **Platform conflict graph edges** | `engine/conflicts.py` | Only HIGH/MEDIUM dispatch | Conflict network visualization |
| 53 | **HDTI hold advisory** (Hold Decision Tradeoff Index) | `engine/ops.py:562` | Computed in `ConnectionCustodyEngine` but never returned via API | "HOLD for X min" action card |

---

## 0.4 COMBINATION GAPS — Pairs never wired together

| # | System A | + System B | = New Capability Nobody Has |
|---|---|---|---|
| **CG-1** | PredictionLedger grade (D5) | AttributionEngine causes (D3) | **"Which cause types do we predict worst?"** — per cause-type MAE/Winkler breakdown. e.g., "Signal-hold predictions: MAE 4.2 min. Weather: MAE 11.8 min." Judges love accountability breakdowns. |
| **CG-2** | PredictionLedger (D5) | DriftMonitor PSI (ml/drift.py) | **"When did we last fail to self-grade?"** — timestamp-linked ledger grades filtered by drift regime. "During FOG regime, our coverage dropped to 71%." |
| **CG-3** | CascadeSimulator (D4) | ConflictScanner (engine/conflicts.py) | **"Which conflicts are cascade amplifiers?"** — simulate conflict without intervention, show downstream inheritance chain. "A hold at CNB triggers 5 downstream inheritances." |
| **CG-4** | SpatialIndex/DaySpatialIndex (D2) | DriftMonitor CUSUM/ADWIN | **"Junction congestion regime change"** — detect when a section transitions from normal to congested based on spatial index data fed to change-point detectors. |
| **CG-5** | RakeResolver is_doomed | ConnectionCustodyEngine hold advisory | **"Rake-doom cascading connection miss"** — when a doomed rake causes a missed connection, auto-flag and quantify. "Doom at NDLS → missed connection at CNB: 47 passengers affected." |
| **CG-6** | PredictionLedger scoreboard | AttributionEngine narrative | **"Honest delay narrative vs our prediction"** — "We predicted +35 min. Actual: +37 min. Primary cause was signal hold, exactly as our model weighted." |
| **CG-7** | Ensemble NNLS weights by horizon | AttributionEngine cause types | **"Why does our long-horizon model degrade?"** — if long-horizon NNLS gives high weight to B3 (linear regression), attribute to lack of causal signal at long range. |
| **CG-8** | Station event 300k dataset | PredictionLedger grades | **"Historical prediction accuracy by day-type/hour"** — offline batch query: "Saturday 18:00 predictions: MAE 8.2 min, coverage 78%. vs weekday 06:00: MAE 4.1 min, coverage 83%." |
| **CG-9** | PSIDriftMonitor | AttributionEngine cause breakdown | **"Drift attribution"** — "After the fog season started, our weather cause attribution accuracy dropped 18%. PSI on `fog_flag` = 0.31 RED." |
| **CG-10** | CascadeSimulator what-if | ConnectionCustodyEngine | **"Intervention ROI"** — "If we hold the connecting train for 10 min at CNB, cascade ripple = +2 min to 3 downstream trains vs saving 47 missed connections." |
| **CG-11** | AdaptiveConformalInference α evolution | Regime detection (fog/rain) | **"Adaptive regime awareness"** — when α drifts up during fog, surface "confidence bands auto-widened by +23% due to fog regime." |
| **CG-12** | DaySpatialIndex | LiveTracker positions | **"Live corridor heatmap"** — at any given minute, render section occupancy as color intensity. This is a network-level view of D2 that NTES has never shown. |

---

*Generated: Phase 0 — Latent Asset Inventory. 12 CG pairs, 36 dead signals, 21 dead data sources, 20 dead capabilities.*
