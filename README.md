# 🚆 RailTwin-X — Real-Time Railway Delay Intelligence & Dispatch Twin

**SIH 2026 · Problem Statement 26028**  
*Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching & Freight Trains*

---

## 🌟 Executive Summary

**RailTwin-X** is an enterprise AI digital twin and neural operational dispatch copilot for Indian Railways (model corridor: New Delhi (NDLS) → Kanpur Central (CNB) → Lucknow Charbagh (LKO), 440 km, 8 stations).

It replaces legacy static delay trackers with a probabilistic **PyTorch Non-Crossing GRU + LightGBM Quantile Ensemble** bounded by a strict kinematic safety interlock. Every served forecast is cryptographically sealed in an append-only **SHA-256 tamper-evident audit ledger**, ensuring zero retrospective score manipulation and verifiable trust for both passengers and section controllers.

---

## 🏆 The 5 Differentiation Surfaces (D1 – D5)

| Surface | Innovation | Hackathon Impact | Verified Metric |
|---|---|---|---|
| **D1: Calibrated Uncertainty Cone** | Outputs $p_{10}-p_{50}-p_{90}$ arrival intervals that widen realistically with distance | Eliminates false "Right Time" certainty; protects passengers from missed onward connections | **80.64% empirical coverage** across 25,203 test samples |
| **D2: Deep Corridor Foresight** | Regional (3h) and corridor-level (6h) delay anticipation incorporating yard queues and rake deficits | Outperforms static NTES by double digits where network complexity compounds | **−36.3% error at 3h** (10.48m vs 16.45m)<br>**−51.7% error at 6h** (14.80m vs 30.67m)<br>*Honest 1h tie: 5.88m vs 5.84m* |
| **D3: Causal Delay Autopsy** | Physics-based decomposition into 7 mutually exclusive causal buckets | 100% exact-sum additivity ($\sum \Delta t_i \equiv \Delta t_{\text{total}}$) with auditable sensor pointers | 7 categories: TSR, Rake inherit, Signal hold, Dwell overrun, Weather fog, Recovery, Residual |
| **D4: Cascade Ripple & Connection Custody DSS** | Quantifies turnaround rake deficits and computes net passenger-hours saved by holding connections | Empowers Section Controllers with an algorithmic trade-off advisory (advisory only) | **+115.0 pax-hours saved** by holding CNB connection 6 min |
| **D5: Tamper-Evident Graded Predictions** | Append-only SHA-256 hash-chained ledger storing all served predictions prior to arrival | Third-party verifiable audit trail; zero retroactive score doctoring | **1,962 blocks chained**, zero integrity breaks (`verify_chain_integrity()`) |

---

## 📊 Canonical Benchmark Proof Table (`ml/artifacts/metrics.json`)

All benchmark metrics were computed using **Rolling-Origin Temporal Cross-Validation** (6 sequential folds, 25,203 test samples):

| Horizon Window | RailTwin-X (ML Quantile) | Baseline 1 (Frozen Delay) | Baseline 2 (Official NTES) | Baseline 3 (Segment Mean) | Auditor Verdict |
|---|---|---|---|---|---|
| **1h Horizon (≤90 km)** | **5.88 min** | 5.84 min | 6.93 min | 10.92 min | **Honest Physics Tie (±0.04m)** |
| **3h Horizon (90–250 km)** | **10.48 min** | 12.79 min | 16.45 min | 13.16 min | **−36.3% vs Official NTES** |
| **6h Horizon (>250 km)** | **14.80 min** | 23.52 min | 30.67 min | 15.65 min | **−51.7% vs Official NTES** |
| **Overall Journey MAE** | **10.72 min** | 14.05 min | 18.02 min | 13.24 min | **−40.5% vs Official NTES** |

> [!NOTE]
> **Honest Physics Disclosure**: Within 90 km, physical train inertia and signaling constraints dominate; RailTwin-X honestly acknowledges that holding the last recorded delay flat achieves 5.84 min MAE, matching our 5.88 min MAE. We publish this tie openly while competitors hide it. Our massive advantage manifests where static trackers fail: at 3 hours (−36.3%) and 6 hours (−51.7%).

---

## 🚀 1-Click Signature Hackathon Demo

### Windows (PowerShell)
```powershell
.\scripts\demo.ps1
```

### Linux / macOS (Bash)
```bash
./scripts/demo.sh
```

The 1-click script starts the FastAPI server on port 8000, launches the Vite frontend on port 5173, and opens your browser directly to the **Signature Live Comparator**:
- **Foresight Console**: `http://localhost:5173/`
- **Live Comparator**: `http://localhost:5173/compare`
- **The Time Machine**: `http://localhost:5173/replay`
- **Ripple & Custody DSS**: `http://localhost:5173/cascade`
- **Honest Model Card**: `http://localhost:5173/model-card`
- **Passenger Mobile View**: `http://localhost:5173/track`

---

## 🧪 Verification & Automated Audits

```bash
# 1. Run full backend unit and regression test suite (268+ tests)
pytest -q

# 2. Verify metric consistency between docs and ml/artifacts/metrics.json
pytest tests/test_doc_metric_consistency.py -v

# 3. Verify SHA-256 hash-chain ledger integrity
python -c "from engine.prediction_ledger import PredictionLedger; valid, count, err = PredictionLedger().verify_chain_integrity(); print(f'Ledger Valid: {valid}, Blocks: {count}')"

# 4. Run frontend production build
cd web && npm run lint && npm run build
```

---

## 📚 Documentation & Technical Defense

- **[5-Minute Demo Runbook](docs/DEMO_RUNBOOK.md)** — Keystroke-by-keystroke presentation script and instant answers to judge trap questions.
- **[Data Provenance & Zero-Mock Policy](docs/DATA_PROVENANCE.md)** — Data sources, feature pipelines, and verifiable SQLite records.
- **[Judge FAQ](docs/JUDGE_FAQ.md)** — Technical defense covering conformal prediction, temporal cross-validation, and scale.
- **[System Architecture](docs/architecture.md)** — Architectural design and module interactions.
- **[Judge One-Pager](docs/judge_onepager.md)** — High-level project summary and metrics overview.
