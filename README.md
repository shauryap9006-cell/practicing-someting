# 🚆 RailTwin-X — Real-Time Railway Delay Intelligence & Dispatch Twin

**SIH 2026 · Problem Statement 26028**  
*Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching & Freight Trains*

---

## 🌟 Overview

**RailTwin-X** is an enterprise-grade AI digital twin and neural operational dispatch copilot for Indian Railways (model corridor: New Delhi `NDLS` $\rightarrow$ Kanpur Central `CNB` $\rightarrow$ Prayagraj `PRYJ` $\rightarrow$ Pt. Deen Dayal Upadhyaya `DDU`).

It replaces legacy deterministic delay calculations with a probabilistic **PyTorch Non-Crossing GRU + LightGBM Ensemble** bounded by a strict kinematic safety interlock. RailTwin-X provides calibrated confidence bands ($q_{10}, q_{50}, q_{90}$), exact minute-by-cause delay attribution, network cascade simulations, and 1-click platform plan re-optimization.

---

## 📐 System Architecture

1. **Telemetry & Live Data Ingestion**: Live adapters (RapidAPI / mock replay), data quality validation gates, and snapshot storage.
2. **ML Prediction Subsystem**: PyTorch sequence model (`ml/model_seq.py`) + LightGBM quantile regressors (`ml/train.py`) stacked via Non-Negative Least Squares (NNLS) with Conformalized Quantile Regression (CQR).
3. **Deterministic Safety Interlock**: Zero-ML rule engine (`safety/interlock.py`) clamping unphysical predictions to physical locomotive limits.
4. **Operations & Re-Optimization Engine**: Network cascade simulator and sub-50ms conflict detection / platform re-scheduler (`engine/conflicts.py`, `engine/ops.py`).
5. **Real-Time API & Dispatch Dashboard**: FastAPI async backend streaming Server-Sent Events (SSE) and reactive React + TypeScript dashboard.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- SQLite 3

### Backend Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the FastAPI API server
uvicorn api.main:app --reload --port 8000
```
API Documentation available at: `http://localhost:8000/docs`

### Frontend Setup
```bash
# 1. Navigate to frontend directory
cd web

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```
Dashboard available at: `http://localhost:5173`

---

## 🧪 Running Tests

```bash
# Run backend test suite
pytest -q
```

---

## 📚 Project Documentation

Official project guides and documentation are maintained in [`docs/`](docs/):
- **[System Architecture](docs/architecture.md)** — Architectural design and module interactions.
- **[Demo Runbook](docs/demo_runbook.md)** — Step-by-step instructions for running the end-to-end demo.
- **[Judging Materials](docs/judge_onepager.md)** — One-pager summary and Q&A reference.
- **[Data & Ops Pipelines](docs/pipelines/README.md)** — In-depth specifications for all core pipelines.
- **[Product Requirements Document (PRD)](PRD.md)** — Scope, user personas, and feature acceptance criteria.
- **[Changelog](CHANGELOG.md)** — Version history and release notes.

---

## 📦 Historical Agent Archive

Agent working logs, preliminary audit notes, and swarm scratchpads have been cleanly consolidated into [`_agent_archive/`](_agent_archive/):
- `_agent_archive/root_logs/` — Historical project summaries and planning files.
- `_agent_archive/control_room/` — Audit sprint logs and diagnostic reports.
- `_agent_archive/swarm_runs/` — Subagent dispatch, briefing, and progress records.
