# RailTwin-X v4 — One-Pager Summary

**Team:** SIH 2026 · Problem Statement PS 26028  
**System:** RailTwin-X Dynamic ETA Forecast & Operational Twin  
**Version:** 4.0 (September 2026) · Ground Truth Audited

---

## Problem Statement

Indian Railways operates 13,000+ trains daily. A delay at one station cascades across the network — but today's tools give passengers and dispatchers only a static "X minutes late" number with no confidence interval, no causal breakdown, and no forward-looking cascade prediction.

**PS 26028 asks:** Build a real-time, ML-powered dynamic ETA forecasting engine that provides calibrated uncertainty intervals, explainable causal autopsies, and actionable Section Controller decision support.

---

## What RailTwin-X Delivers (The Five Differentiators)

| Capability | Technical Implementation | Demonstrated Result |
|---|---|---|
| **D1. Calibrated Uncertainty** | Conformal Quantile Regression (p10–p50–p90) | **80.64%** empirical coverage · Winkler **57.94** |
| **D2. 3–6h Foresight** | Multi-horizon ensemble with physical momentum | 3h MAE **10.48 min** (−36.3%) · 6h MAE **14.8 min** (−51.7%) |
| **D3. Causal Delay Autopsy** | 7-bucket mechanistic decomposition | $\sum$ causes $\equiv \Delta$delay (exact mathematical additivity) |
| **D4. Cascade & Custody DSS** | Discrete-event SimPy ripple + passenger-hours trade-off | Advisory DSS for Section Controllers with pax-hr optimization |
| **D5. Graded Audit Ledger** | SHA-256 hash-chained immutable prediction ledger | Provably non-retro-edited receipts verified on-demand |

---

## Architecture (3 Tiers + Safety Interlock)

```
Tier 1 (Historical Lookup) ─┐
Tier 2 (LightGBM CQR)      ─┼─► BrainOrchestrator ─► Safety Interlock ─► ConflictScanner ─► Controller Advisory
Tier 3 (PyTorch GRU Chall) ─┘       (5 deterministic rules, no ML)         (3 rule types)
```

- **Overall Benchmark:** Test MAE **10.72 min** · Overall 80% Coverage **80.64%** · Winkler **57.94** · CRPS **7.44**
- **1h Horizon Scientific Honesty:** At 1h (<=90km), train physics and frozen delay tie (**5.88 min** vs **5.84 min** B1 baseline) — we publish this tie openly while competitors fabricate short-horizon ML gains.
- **3h–6h Horizon Advantage:** Where Where Is My Train and NTES freeze, RailTwin-X outperforms official run-rate by **−36.3%** at 3h and **−51.7%** at 6h.

---

## Key Numbers (Held-Out Test Week — Canonical Artifacts)

| Horizon | RailTwin-X MAE | B1 Frozen Delay | B2 Official NTES | vs B2 Official | 80% Band Coverage | Winkler Score |
|---|---|---|---|---|---|---|
| **1 hour** (<=90km)   | **5.88 min**  | 5.84 min | 6.93 min | −15.1% (±0 physics tie) | 70.3% | 27.83 |
| **3 hours** (90-250km) | **10.48 min** | 12.79 min | 16.45 min | **−36.3%** ✅ | 73.3% | 44.80 |
| **6 hours** (>250km)   | **14.8 min** | 23.52 min | 30.67 min | **−51.7%** ✅ | 98.4% | 98.87 |

*Overall Held-Out Test Set: **10.72 min MAE** across 25,203 samples · **80.64%** coverage.*

---

## What Makes It Different (Honesty Armor)

1. **Calibrated Foresight, Not Current Location** — commodity apps tell you where a train WAS; RailTwin-X tells you where the network WILL BE 3–6 hours ahead.
2. **Exact Causal Accounting** — every delay minute is accounted for across 7 buckets (RAKE_INHERIT, TSR_ACTIVE, WEATHER_FOG, WEATHER_RAIN, PLATFORM_WAIT, CONGESTION, UNEXPLAINED).
3. **SHA-256 Hash-Chained Audit Ledger** — every prediction generates an immutable receipt before truth is revealed, guaranteeing zero cherry-picking.
4. **Section Controller Advisory Authority** — DSS advisory only; operational hold decisions calculate net passenger-hours saved and leave dispatch authority with the Section Controller.
