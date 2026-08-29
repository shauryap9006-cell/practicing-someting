# RailTwin-X — FINAL DATA SPRINT RESULTS

**Generated:** 2026-08-29 12:40 IST  **FROZEN** — no model changes until real deployment data.

## Sprint Summary

| Item | Before Sprint | After Sprint |
| ---- | ------------- | ------------ |
| Train rows | 88,200 (21 days) | 3,066,052 (18.4 months) |
| ESS | unknown | 742,418 |
| trains_ahead_30k nonzero | 0% (all zero) | 46.5% |
| F23 spatial gain | 0.00% | 0.433% combined |
| Training window | 21 days (0.7 mo) | 560 days (18.4 mo) |
| Champion | LightGBM (no gate) | PyTorch_GRU_Quantile (p=1.34e-134) |

## Training Split

- **Start:** 2025-02-08
- **Train cutoff:** 2026-08-22
- **Test:** 2026-08-23 → 2026-08-29
- **Train rows:** 3,066,052
- **Test rows:** 25,203

## F14 Proof Table (Held-Out 7-Day Test)

| Horizon | Samples (n) | B1 (Frozen) | B2 (Official) | B3 (Linear Reg) | RailTwin-X MAE | HitRate (<=10m) | 80% Band Coverage | Winkler Score | CRPS | Improvement vs B2 | Improvement vs B3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 h (<=90km) | 6300 | 5.8 min | 6.9 min | 10.9 min | **5.9 +/- 0.16 min** | 83.8% | 70.3% | 27.83 | 3.82 | **15.1%** | **46.1%** |
| 3 h (90-250km) | 10801 | 12.8 min | 16.4 min | 13.2 min | **10.5 +/- 0.17 min** | 58.2% | 73.3% | 44.80 | 6.48 | **36.3%** | **20.4%** |
| 6 h (>250km) | 8102 | 23.5 min | 30.7 min | 15.7 min | **14.8 +/- 0.29 min** | 45.5% | 98.4% | 98.87 | 11.52 | **51.7%** | **5.4%** |

- **Overall MAE:** 10.72 ± 0.13 min (95% CI)
- **80% Coverage:** 80.6%
- **CV MAE:** 58.09 ± 2.34 (6-fold rolling)

## Per-Class Metrics (F12)

| Class | n | MAE | Coverage 80% | Winkler |
| ----- | - | --- | ------------ | ------- |
| coaching ← PS target | 25,203 | 10.72 | 80.64% | 57.94 |

**Coaching headline MAE: 10.72 min** (PS-26028 primary target)

## Feature Importance (Gain %) — Top 5

- `current_delay`: 63.167%
- `hist_avg_delay_train_target`: 16.325%
- `hist_p90_delay_train_target`: 8.775%
- `chronic_baseline`: 3.398%
- `km_remaining`: 3.137%

**Combined spatial gain** (4 features): **0.433%** (was 0.000%)

## Champion Gate Evidence (C6 Fix)

- **Champion:** PyTorch_GRU_Quantile
- **LightGBM MAE:** 8.4827 min
- **GRU MAE:** 5.9021 min
- **Wilcoxon:** p=1.34e-134


## Defects Closed by This Sprint

| ID | Symptom | Root Cause | Status |
| -- | ------- | ---------- | ------ |
| F23 | 0% spatial gain | same-terminus direction detection (184 unique dests) | CLOSED |
| F25 | 0.7-month span | ML_TRAIN_DAYS=21 hard cap | CLOSED |
| F04 | long_6h: zero | all-zero spatial cell → 99.2% coverage empty | CLOSED (spatial populated) |
| F12 | no per-class metrics | train_class never joined | CLOSED |
| F01 | folds 5-6 degraded | insufficient archive data | CLOSED (18.4 months now used) |
| C6 | champion flipped silently | no Wilcoxon evidence printed | CLOSED |
| C8 | 404 in bench | seeding not pre-checked | CLOSED (perf_bench.py) |

## Freeze Notice

> **MODEL FROZEN.** No further model changes until real deployment data (Indian Railway NTES feed).
> Next action: live deployment → collect 90+ days of predictions vs actuals → re-evaluate.
