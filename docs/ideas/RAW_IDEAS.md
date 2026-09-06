# PHASE 2 — RAW IDEAS (seeded, divergent)
**Each idea: name, one-liner, D it deepens, files reused, 60s demo moment.**

> **STATUS UPDATE 2026-09-05 (commit `f371ecb` + working tree):**
> - **A5** (Connection Risk + HOLD) → **SHIPPED** as ripple-board hold advisories with passenger-hours (`RippleBoardPage`, `/v1/cascade/ripple`).
> - **B1-lite** (shock injection demo) → **SHIPPED** (`/v1/demo/inject-event` + `ComparatorPage` cone reaction). Full counterfactual A/B remains narrative.
> - **B2** (Rake Doom) → **controller half SHIPPED** (ripple board); passenger doom card still open.
> - **C1-backtest** → **SHIPPED** (`HonestModelCardPage`, `/v1/model/performance`). C1-live-ledger (the hash-chained part) still open — endpoints exist, no UI.
> - **D2-lite** (honest horizon cards) → **SHIPPED** within the model card.
> - New pages: `ForesightConsolePage` (now `/` root), `TimeMachinePage`, `ComparatorPage`, `RippleBoardPage`, `HonestModelCardPage`. Routes in `web/src/App.tsx:63-68`.
> - **NEW LIABILITY discovered:** `TimeMachinePage.tsx:64-94` displays **hardcoded mock receipt hashes** presented as "Sealed / SHA-256 Chain Intact" — must be fixed or relabeled before judging (see FINAL_RECOMMENDATIONS §6).

---

## CATEGORY A — DECISIONS FROM UNCERTAINTY (D1 → action)

### A1. "Leave-Now Advisory"
- **One-liner:** Off p10 — if you must board, leave home so you make even the earliest band.
- **D:** Deepens D1 (calibrated distribution)
- **Reuses:** `engine/prediction_ledger.py:104` (graded receipts), `api/predictor.py:451` (enforce_quantile_order), `engine/clocks.py` (now-iso).
- **Logic:** For each active train at major stations, compute `board_leave_home_by = sched_dep - (p10_min + 30)` minutes; show as a "leave by 18:55" badge on the train detail panel.
- **60s demo:** Click train 12556 → see arrival band [18:30, 19:05, 19:45]; below band: "LEAVE BY 18:55 to catch even earliest arrival." Judge reacts: "I have never seen an ETA app tell me when to leave home."

### A2. "Confidence-Gated Alert"
- **One-liner:** Fire alert ONLY when the band shifts by ≥X minutes (not when delay ticks up).
- **D:** Deepens D1 + D5
- **Reuses:** `engine/conformal.py:46` (Winkler), `engine/prediction_ledger.py:104` (grade_actual_arrival for threshold calc), `notifications/types.py`.
- **Logic:** Compute `band_shift = current_p10 - previous_p10`. Only fire when band shifts AND low confidence.
- **60s demo:** During demo scenario, injection at CNB causes band to widen from [15, 30, 50] → [25, 45, 75]; alert fires once with "Band widened: regime shift detected."

### A3. "Best-Case vs Worst-Case Schedule"
- **One-liner:** Show the schedule IF the train hits p10, IF p50, IF p90 — as 3 parallel timelines.
- **D:** Deepens D1
- **Reuses:** `api/predictor.py:467` (best_arr / likely_arr / worst_arr) — already computed and returned.
- **60s demo:** Three colored Gantt rows for one train showing all three schedules.

### A4. "Punctuality Card — Percent of trains we nailed"
- **One-liner:** "Today: 91% of our predictions hit actual within ±5 min."
- **D:** Deepens D5 (self-accountability)
- **Reuses:** `engine/prediction_ledger.py:187` (`get_calibration_scoreboard`)
- **60s demo:** Card on scoreboard: "Today: 138 predictions made, 91% within ±5 min. Yesterday: 92%. 7-day rolling: 89%."

### A5. "Connection Risk Disclosure (asset #9)"
- **One-liner:** Show percentage chance each connection holds; HOLD advisory.
- **D:** Deepens D1 + D4
- **Reuses:** `engine/ops.py:459` (ConnectionCustodyEngine, already computes 4 probability buckets)
- **60s demo:** Junction board at CNB: incoming 12556 (p10/p50/p90) → outgoing 12448 in 25 min → "62% hold probability, HOLD FOR 8 MIN saves 34 passenger-hours." Judge: "this is actually operational."

---

## CATEGORY B — COUNTERFACTUAL SURFACES (D4 → what-if)

### B1. "What-If Intervention Lab"
- **One-liner:** "Hold 12556 at CNB for 10 min" → ripple map of cascading downstream delays.
- **D:** Deepens D4
- **Reuses:** `engine/simulator.py:57` (`run_simulation`), `engine/simulator.py:304` (`get_train_autopsy`), `engine/rakes.py:57` (rake inheritance).
- **Logic:** Frontend slider for train × station × minutes; backend calls simulator twice (baseline vs intervention); diff = ripple impact.
- **60s demo:** "If I hold 12556 at CNB for 10 min, train 12448 inherits +6 min, train 12248 inherits +4 min. NET IMPACT: +47 min cascade vs 0 passenger benefit. Recommendation: DO NOT INTERVENE." Judge: jaw-drop.

### B2. "Rake Doom Early-Warning"
- **One-liner:** Show incoming rake late → outgoing train doomed; quantifies cascade before actual departure.
- **D:** Deepens D4 (rake links + cascade)
- **Reuses:** `engine/rakes.py:57` (RakeDoomStatus, `is_doomed`)
- **60s demo:** Card on outgoing train: "DOOMED: incoming rake 12034 arrived +45 min late. Your train 12556 will depart ~19:45 (+45 min)."

### B3. "Optimal Hold Calculator"
- **One-liner:** Compute optimal hold at junction to maximize passenger connection rate.
- **D:** Deepens D1 + D4
- **Reuses:** `engine/ops.py:459` (HDTI hold_advisory)
- **60s demo:** At CNB, dragging a slider from 0 → 30 min hold → live graph shows connection success rate rising from 62% → 96% at +10 min hold.

---

## CATEGORY C — SELF-ACCOUNTABILITY PRODUCTS (D5 → public trust)

### C1. **"Honesty Scoreboard"** (world-first)
- **One-liner:** Live "Our last 1000 predictions: MAE 5.88 min, coverage 80.6%, Winkler 27.8" page.
- **D:** Deepens D5
- **Reuses:** `engine/prediction_ledger.py:187` (get_calibration_scoreboard), `ml/conformal.py:46` (Winkler score already computed per ledger row).
- **Logic:** Aggregate ledger, return scoreboard JSON; render as a public dashboard.
- **60s demo:** Live page shows live numbers ticking as predictions are graded. "✓ Chain intact · ✓ 12,847 verified · MAE 5.88 · Coverage 80.6% · Winkler 27.8."

### C2. "Per-Cause-Type Accuracy"
- **One-liner:** "We predict signal-hold delays at MAE 4.2 min. Weather at MAE 11.8 min."
- **D:** Deepens D3 + D5
- **Reuses:** `engine/attribution.py:145` (`decompose_train_delay`), `engine/prediction_ledger.py:104` (graded receipts), join on (train, station, primary_cause).
- **60s demo:** Bar chart showing MAE per cause category. Judge: "Nobody publishes this."

### C3. "Tamper-Evident Audit Receipt"
- **One-liner:** Each prediction carries a SHA-256 receipt hash; show "verified ✓" badge.
- **D:** Deepens D5
- **Reuses:** `engine/prediction_ledger.py:57` (`record_prediction_receipt`), `engine/prediction_ledger.py:159` (`verify_chain_integrity`)
- **60s demo:** Hover prediction → "Receipt: 0x8a3f...c12 · Chain verified · Verified at 18:45 by 12,847 prior receipts"

### C4. "Prediction Receipt Browser"
- **One-liner:** Searchable ledger of every prediction ever made with verification status.
- **D:** Deepens D5
- **Reuses:** `engine/prediction_ledger.py` (entire module)
- **60s demo:** Type a train number → see its full prediction history with verification status per entry.

### C5. "Real-Time Self-Grade Ticker"
- **One-liner:** As actual arrivals happen, show "✓ prediction #12448: predicted +12, actual +14, in-band ✓".
- **D:** Deepens D5
- **Reuses:** `engine/prediction_ledger.py:104` (grade_actual_arrival), `engine/live_tracker.py:322` (auto-grade on tick).
- **60s demo:** Ticker scrolling recent grades in real time.

---

## CATEGORY D — NETWORK-LEVEL FORESIGHT (D2 → the whole network)

### D1. **"6-Hour Corridor Congestion Radar"**
- **One-liner:** Live heatmap of section occupancy across the corridor for the next 6 hours.
- **D:** Deepens D2
- **Reuses:** `engine/spatial_context.py:152` (DaySpatialIndex, 1440×N grid), `engine/live_tracker.py` (live positions)
- **Logic:** Roll the spatial index forward by 6 hours using current delays; render as colored section heatmap.
- **60s demo:** Animated corridor with sections colored red (high occupancy), amber, green, plus time slider 0–6h. "At 14:00, CNB-DDUA section is projected at 87% occupancy."

### D2. "Junction Pressure Forecast"
- **One-liner:** Per-junction pressure score for the next 6 hours — predicts conflicts before they form.
- **D:** Deepens D2 + D4
- **Reuses:** `engine/conflicts.py:76` (ConflictScanner), `engine/spatial_context.py`
- **60s demo:** Junction list at CNB with conflict risk badges.

### D3. "Train Position Certainty Heatmap"
- **One-liner:** Overlay confidence on the live map — train faded = uncertain position.
- **D:** Deepens D2 + D3
- **Reuses:** `engine/live_tracker.py:433` (confidence decay), `engine/position_resolver.py` (position entropy)
- **60s demo:** Map with trains at varying opacity per confidence; click train → see "most likely km X, but could be Y/Z."

---

## CATEGORY E — REGIME AWARENESS (drift/fog → visible intelligence)

### E1. **"Model Regime Badge"**
- **One-liner:** "REGIME: WINTER FOG — intervals widened 22% due to low visibility history."
- **D:** Deepens D1 + drift
- **Reuses:** `ml/drift.py:34` (PSI), `ml/conformal.py:216` (ACI α), `engine/weather.py`
- **60s demo:** Badge on scoreboard; click → "Fog regime started 2025-12-15; α has drifted from 0.20 → 0.27."

### E2. **"Behavior Anomaly Early-Warning"**
- **One-liner:** "Train 12556 velocity profile shifted at 14:32 — possible signal failure."
- **D:** Deepens D3 + drift
- **Reuses:** `ml/drift.py:73` (CUSUM), `ml/drift.py:98` (ADWIN)
- **60s demo:** CUSUM trigger → alert card on dashboard.

### E3. "Coverage-By-Regime Decomposition"
- **One-liner:** "Coverage in fog: 78%. Coverage in clear weather: 84%."
- **D:** Deepens D5 + drift
- **Reuses:** `engine/prediction_ledger.py:104` + weather join
- **60s demo:** Split scoreboard by regime; judges see honesty.

---

## CATEGORY F — HISTORICAL INTELLIGENCE (300k events → searchable truth)

### F1. **"Why Was My Train Late Last Tuesday?"**
- **One-liner:** Searchable historical autopsy over 300k events; passenger can query any train × any date.
- **D:** Deepens D3 + historical
- **Reuses:** `engine/attribution.py:145`, `data/station_events` (300k rows)
- **60s demo:** Type "12556, 2026-08-15" → full autopsy with causes summing to 47 min exactly.

### F2. "Corridor Historical Heatmap"
- **One-liner:** Time × section heatmap of average delay over 6 months.
- **D:** Deepens D2 + historical
- **Reuses:** `data/station_events`
- **60s demo:** Click section → see "this section causes 23% of all delay-minutes."

### F3. "Cause Frequency Leaderboard"
- **One-liner:** Top causes of delays across the corridor over 6 months.
- **D:** Deepens D3 + historical
- **Reuses:** `engine/attribution.py` + `data/station_events`
- **60s demo:** "Most common cause: signal hold (34%), weather (18%), platform wait (15%)..."

---

## CATEGORY G — PRACTICAL UNIQUE UTILITY

### G1. **"Refund Eligibility Detector"** (verify IR rules)
- **One-liner:** Auto-detect if a passenger's delay qualifies for TDR refund per IR rules.
- **D:** Deepens D1 + D3 + ledger
- **Reuses:** `engine/prediction_ledger.py:104` (graded receipts, our own actual_delay vs predicted), `engine/attribution.py` (causes), `data/station_events` (300k rows).
- **CAUTION:** IR rules require verification. Per Indian Railways Catering & Tourism Corporation (IRCTC) Tatkal & refund rules:
  - **3+ hours delay on Rajdhani/Shatabdi/Duronto/Vande Bharat**: full refund
  - **2+ hours delay**: 50% refund (subject to class)
  - Passenger must file TDR within specified window
- **Our angle:** Use our graded ledger (which has actual_delay captured) to detect eligible cases automatically and surface a "you may be eligible for refund" card. NOT generating the certificate — just eligibility detection.
- **60s demo:** Show last week's delays; for any train that arrived 3+ hours late, flag "TDR eligible: +185 min actual."

### G2. **"Onward-Journey Cascade Planner"**
- **One-liner:** When your train is delayed, show which connecting trains you can still catch.
- **D:** Deepens D4 + D1
- **Reuses:** `engine/ops.py:459` (ConnectionCustodyEngine)
- **60s demo:** "Train 12556 arriving 14:35 (+45 min). You can still catch 12448 (15:00) — buffer 25 min."

---

## CATEGORY H — NOVEL VISUALIZATION OF EXISTING COMPUTATION

### H1. **"Causal Autopsy Waterfall"**
- **One-liner:** Waterfall chart showing total delay decomposed by cause bucket, each cause a stepped bar.
- **D:** Deepens D3
- **Reuses:** `engine/attribution.py:88` (`AutopsyResult`, `causes`)
- **60s demo:** Click train 12556 → waterfall: 0 → +45 (rake) → +30 (TSR) → +15 (signal) → +90 total. Each bar labeled with evidence pointer.

### H2. **"Confidence Cone"**
- **One-liner:** Animation showing the cone converging on actual arrival time.
- **D:** Deepens D1
- **Reuses:** `engine/prediction_ledger.py:104` (graded receipts — we know actual_delay for past predictions)
- **60s demo:** Animated cone narrowing as train approaches destination; final collapse to actual time.

### H3. **"Cascade Ripple Animation"**
- **One-liner:** Animated shockwave across the network when an injection occurs.
- **D:** Deepens D4
- **Reuses:** `engine/simulator.py:57`
- **60s demo:** Inject 45-min shock at CNB → animated ripple spreading to downstream trains over the corridor.

### H4. **"Prediction Receipt Chain Visualization"**
- **One-liner:** Visualize the SHA-256 hash chain — each block linked to the prior.
- **D:** Deepens D5
- **Reuses:** `engine/prediction_ledger.py:159` (`verify_chain_integrity`)
- **60s demo:** Animated chain of blocks growing as new predictions arrive; click block → see prediction details.

### H5. **"Drift Indicator Gauge"**
- **One-liner:** PSI meter per feature, with traffic-light color coding.
- **D:** Deepens D5 + drift
- **Reuses:** `ml/drift.py:34`
- **60s demo:** Live gauge showing 7 features; click RED feature → see distribution shift graph.

---

## WILD CARDS — Beyond categories

### W1. "Evidence Tracer" — Click any cause → SQL trace to evidence record.
- **Reuses:** `engine/attribution.py:38` (`EvidencePointer`), `data/station_events`, `data/speed_restrictions`, `data/weather`.

### W2. "Prediction Aging Timeline" — When was this prediction made? When did it get graded?
- **Reuses:** `engine/prediction_ledger.py:160` (query_timestamp vs actual_timestamp).

### W3. "Model Provenance Card" — Click "Why this prediction?" → show model version, SHA-256, training date, calibration q_hat.
- **Reuses:** `ml/artifact_integrity.py`, `api/predictor.py:188` (`get_model_info`).

### W4. "What We Don't Know" — Show the system KNOWING what it doesn't know (uncertainty visualization for unresolved questions).
- **Reuses:** `ml/conformal.py` (coverage), `engine/position_resolver.py` (entropy).

### W5. "Phase-of-Day Coverage Map" — Show 80% band coverage by hour-of-day.
- **Reuses:** `engine/prediction_ledger.py:104` + join with weather/hour.

---

## ANTI-PATTERNS (auto-rejected)
- Generic LLM chatbot (unless 100% grounded in attribution)
- "Blockchain" buzzword (we say hash-chained audit ledger)
- Gamification with zero rubric value
- Anything needing data we don't have (e.g., PNR ↔ train mapping for live passenger PNR → auto-notify)

---

*Generated: Phase 2 — Raw Ideas. 27 ideas across 8 categories + 5 wild cards. All reference real files.*
