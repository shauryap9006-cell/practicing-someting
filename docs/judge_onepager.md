# RailTwin-X v4 — One-Pager Summary

**Team:** SIH 2026 · Problem Statement PS 26028  
**System:** RailTwin-X Delay Intelligence Engine  
**Version:** 4.0 (August 2026)

---

## Problem Statement

Indian Railways operates 13,000+ trains daily. A delay at one station cascades across the network — but today's tools give passengers and dispatchers only a static "X minutes late" number with no confidence interval, no causal breakdown, and no forward-looking cascade prediction.

**PS 26028 asks:** Build a real-time, ML-powered delay prediction system that gives accurate ETAs with confidence intervals and automated dispatcher advisories.

---

## What RailTwin-X Delivers

| Capability | Technical Implementation | Demonstrated Result |
|---|---|---|
| **Probabilistic ETA** | CQR-calibrated LightGBM + PyTorch GRU | 1h MAE **7.4 min** · 80% coverage **81%** |
| **Cascade Simulation** | SimPy DES with exact ledger attribution | 100% delay minute accounting |
| **Conflict Detection** | Deterministic 3-rule safety scanner | 0% ML in safety rules |
| **Dispatcher Advisory** | BrainOrchestrator ML→Safety→Conflicts pipeline | Human ACK required |
| **DFC Freight Support** | 5 freight classes · WDFC/EDFC corridor routing | 14m coal headway enforcement |
| **Production-Ready** | Docker · Makefile · Nightly PSI drift monitor | 78/78 tests green |

---

## Architecture (3 Tiers)

```
Tier 1 (Historical Lookup) ─┐
Tier 2 (LightGBM CQR)      ─┼─► BrainOrchestrator ─► Safety Interlock ─► ConflictScanner ─► Advisory
Tier 3 (PyTorch GRU Attn)  ─┘       (5 deterministic rules, no ML)         (3 rule types)
```

- **Tier 3 (Champion):** PyTorch GRU + Temporal Attention + Non-crossing quantile heads  
  - Test MAE **7.29 min** · 80% Coverage **87.4%** · Crossing violations **0**
- **Tier 2 (Challenger):** 6 LightGBM boosters (1h/3h/6h × p10/p50/p90) + per-horizon CQR calibration
- **Ensemble:** Wilcoxon promotion gate (p=0.0000) · √hops CQR autoregressive rollout

---

## Key Numbers (Held-Out Test Week)

| Horizon | MAE | vs Baseline-2 | vs Baseline-3 | 80% Coverage |
|---|---|---|---|---|
| 1 hour  | **7.4 min**  | −26.2% ✅ | −18.8% ✅ | 81.1% ✅ |
| 3 hours | **12.2 min** | −51.9% ✅ | −1.7% ✅  | 82.5% ✅ |
| 6 hours | **17.2 min** | −64.5% ✅ | −2.6% ✅  | 99.5% ✅ |

---

## What Makes It Different

1. **Non-crossing quantile heads** — p10 ≤ p50 ≤ p90 mathematically guaranteed (not just hoped for)
2. **Exact causal attribution** — every delay minute traced to CROSSING\_HOLD / TSR / PLATFORM\_WAIT / RAKE\_INHERIT / EMPTY\_RETURN
3. **DFC Freight awareness** — 14 min coal headway vs 5 min passenger; empty-return cascade propagation
4. **Human-in-the-loop by design** — all advisories require dispatcher ACK; full audit trail in DB
5. **PSI drift monitor** — nightly feature distribution check; RED alert triggers retrain
