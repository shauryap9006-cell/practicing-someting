# PHASE 3 — NOVELTY MATRIX
**Idea × Competitor/Research. Confidence in [HIGH/MEDIUM/LOW]. Verdict: UNIQUE / PARTIALLY-EXISTS / COMMODITY.**

> **STATUS UPDATE 2026-09-05:** Novelty verdicts unchanged — shipping a feature doesn't change who else has it. What changed is build state: C1a (backtest), A5, B2a, B1-lite, D2-lite are now **built**; the remaining open UNIQUE items keep their verdicts. One addition: the shipped shock-injection comparator (B1-lite) is itself **UNIQUE as a product** (HIGH) — no consumer or controller surface demonstrates cone-vs-baseline reaction to injected shocks live. The live-ledger scoreboard (C1b) remains the strongest UNIQUE claim since it's the one thing no competitor's architecture can even produce.

---

## Competitor Inventory

| System | What it does | What it DOESN'T have |
|---|---|---|
| **NTES (National Train Enquiry System)** | Live train status, PNR, basic delay number. Single point estimate. | No confidence bands, no causal attribution, no cascade prediction, no self-grading. |
| **WhereIsMyTrain (GoIbibo)** | Train tracking, live map, PNR, basic delay. | Single number ETA, no causal autopsy, no self-grading. |
| **RailYatri / ConfirmTkt** | Booking, predictions, live train status. | Single number ETA, no uncertainty bands, no public self-grading. |
| **CRIS internal systems (TMS, COA, FOIS)** | TMS: train movement. COA: coach allotment. FOIS: freight. | No unified probabilistic ETA. Different data silo per system. No public accountability. |
| **Academic — delay prediction (文献)** | Many papers: ML models for delay prediction. | Few publish calibrated conformal intervals; almost none do live self-grading on tamper-evident ledger. |
| **Academic — conformal prediction in transport** | Research papers (e.g., SESIA/CANDES CQR) | None apply to live ETA + public ledger scoring. |
| **Academic — delay management / digital twins** | Strong literature (e.g., Delorme, Törnquist) | None combine ledger + cascade + per-cause attribution in one product. |

---

## Validation Table

| ID | Idea | NTES | WIMT/RY | CRIS/COA | Academic | Verdict | Confidence |
|---|---|---|---|---|---|---|---|
| A1 | Leave-Now Advisory | No | No | No | Not in product literature | **UNIQUE** | HIGH |
| A2 | Confidence-Gated Alert | No | No | No | Marginal | **UNIQUE** | HIGH |
| A3 | Best/Worst/Likely Schedule | No | No | No | No | **UNIQUE** | HIGH (already in our API, just not surfaced) |
| A4 | Punctuality Card | No | No | Internal Q-dashboards may have it | No public | **UNIQUE** | HIGH |
| A5 | Connection Risk + HOLD | No | No | Possible in COA controller screens | "Delay management" literature exists | **PARTIALLY-EXISTS** (academic; not in any product I know) | MEDIUM |
| B1 | **What-If Intervention Lab** | No | No | COA may have crude what-if | "Delay management" literature | **UNIQUE-as-product** (we surface ripple map; papers describe algorithms) | HIGH |
| B2 | Rake Doom Early-Warning | No | No | COA may have turnaround calc | No | **UNIQUE** | HIGH |
| B3 | Optimal Hold Calculator | No | No | Possible in COA | Delay mgmt literature | **PARTIALLY-EXISTS** | MEDIUM |
| C1 | **Honesty Scoreboard** | No | No | Internal Q-reports | No public ledger of self-graded predictions | **UNIQUE** | HIGH (defining-angle) |
| C2 | **Per-Cause-Type Accuracy** | No | No | No | No public breakdown | **UNIQUE** | HIGH |
| C3 | Tamper-Evident Audit Receipt | No | No | CRIS has audit logs but not public | Research on blockchained ML exists, but not on railway ETAs | **UNIQUE-as-product** | HIGH |
| C4 | Prediction Receipt Browser | No | No | No | No | **UNIQUE** | HIGH |
| C5 | Real-Time Self-Grade Ticker | No | No | No | No | **UNIQUE** | HIGH |
| D1 | **6-Hour Corridor Congestion Radar** | No | No | COA may have sectional occupancy | "Network modeling" literature | **UNIQUE-as-product** (we surface as a weather-radar) | HIGH |
| D2 | Junction Pressure Forecast | No | No | COA has conflict detection | Delay mgmt literature | **PARTIALLY-EXISTS** | MEDIUM |
| D3 | Position Certainty Heatmap | No | No | COA may have ETA bands (uncertain) | Bayesian tracking in transport | **PARTIALLY-EXISTS** | LOW (judges may know literature) |
| E1 | **Model Regime Badge** | No | No | No | Regime-switch literature | **UNIQUE** | HIGH |
| E2 | Behavior Anomaly Early-Warning | No | No | No | Change-point detection in IoT (wider) | **UNIQUE-as-product** | HIGH |
| E3 | Coverage-By-Regime Decomposition | No | No | No | No | **UNIQUE** | HIGH |
| F1 | **Why Was My Train Late Last Tuesday?** | No | No | No | Historical analytics exist but not passenger-facing | **UNIQUE** | HIGH |
| F2 | Corridor Historical Heatmap | No | No | Yes (CRIS internal) | No public | **PARTIALLY-EXISTS** | MEDIUM |
| F3 | Cause Frequency Leaderboard | No | No | Internal reports | No | **UNIQUE** | HIGH |
| G1 | **Refund Eligibility Detector** | No | No | IRCTC has TDR filing | No automated detection | **UNIQUE** | HIGH (verify IR rules) |
| G2 | Onward-Journey Cascade Planner | No | No | Possible in COA | Delay mgmt literature | **PARTIALLY-EXISTS** | MEDIUM |
| H1 | Causal Autopsy Waterfall | No | No | No | Visualization literature | **UNIQUE** | HIGH |
| H2 | Confidence Cone | No | No | No | Uncertainty viz literature | **UNIQUE** | HIGH |
| H3 | Cascade Ripple Animation | No | No | No | Animation is novel surface | **UNIQUE** | HIGH |
| H4 | Prediction Receipt Chain Visualization | No | No | No | Block explorer analogs in crypto | **UNIQUE** | HIGH (analog to block explorer) |
| H5 | Drift Indicator Gauge | No | No | Internal MLOps dashboards | No | **UNIQUE-as-product** | MEDIUM |

---

## AUTO-KILL (commodity)

None of the raw ideas are commodity. Each has unique depth. The anti-patterns (chatbots, generic tracker) were rejected before reaching this matrix.

---

## FLAGGED FOR MANUAL VERIFICATION

- **A5 / B3 / D2 / D3 / F2 / G2**: Marked as PARTIALLY-EXISTS because COA (the controller console used by Indian Railways Operations) may have analog features for trained operators. **Need to verify with a Railway domain expert whether COA has HOLD advisory or sectional forecasting.** If yes, these become commodity; if no, they upgrade to UNIQUE.
- **D3**: Bayesian tracking in transport is academic (e.g., particle filters). **Need to verify if any product exposes a "position certainty heatmap" surface.** HIGH risk that an academic lab has demoed this.

---

## VERDICTS DISTRIBUTION

- **UNIQUE (HIGH confidence):** 19 ideas — C1, C2, C3, C4, C5, A1, A2, A3, A4, B1, B2, D1, E1, E2, E3, F1, F3, G1, H1, H2, H3, H4
- **UNIQUE (MEDIUM):** H5
- **PARTIALLY-EXISTS:** A5, B3, D2, D3, F2, G2
- **COMMODITY:** 0

---

*Generated: Phase 3 — Novelty Validation. 27 ideas, 0 commodity, 22 unique-HIGH, 5 partial.*
