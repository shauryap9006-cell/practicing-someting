# RailTwin-X — Control Room Backlog (03_BACKLOG.md)

**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Audit Date:** 2026-08-28  
**Ordering Rule:** Critical Fixes (TASK-01 to TASK-03) → Performance Optimization (TASK-04 to TASK-06) → Packaging & Cleanup (TASK-07 to TASK-12)

---

## 1. Definitive Audit Remediation Backlog (12 Tasks)

| Task ID | Priority | Subsystem | Target File & Line | Task Title & Action Required | Verification Command |
|---|---|---|---|---|---|
| **TASK-01** | **P0 (BLOCKER)** | `api/` | `api/predictor.py:96-115` | **Fix `current_seq` Default Query Resolution**<br>Query `station_events` for real live train location when `current_seq` is not explicitly provided, resolving Complaint C2 & C3. | `python -m pytest tests/test_api.py -k test_api_train_journey` |
| **TASK-02** | **P0 (BLOCKER)** | `web/` | `web/src/pages/dashboard/*.tsx` | **Wire 12 Core Dashboard Pages from `mockStore` to Live API**<br>Replace `import { mockStore }` with `import { api }` in Overview, Trains, TrainDetail, Gantt, Advisories, Map, Model, etc. | `cd web && npm run build` |
| **TASK-03** | **P1 (HIGH)** | `web/` | `web/src/lib/api.ts` | **Fix 12 Mismatched Endpoint URLs and HTTP Methods**<br>Fix TSR lift (`DELETE`), SOP start (`/start`), crew sign-on (`/sign-on`), and infra routes (`/infrastructure/*`). | `python -m pytest tests/test_api.py` |
| **TASK-04** | **P1 (HIGH)** | `api/` | `api/routes.py:90` | **Singleton Cache Historical Baseline Recalculation**<br>Memoize baseline statistics in `PredictorService`, dropping journey timeline latency from 945ms to <25ms (Fixes C1). | `python scratch/bench_clean.py` |
| **TASK-05** | **P1 (HIGH)** | `api/` | `api/board_routes.py:123-128` | **Vectorize Batch Predictions in Live Station Board**<br>Replace sequential per-train prediction loop with vectorized batch snapshot prediction on `/api/board/live`. | `python -m pytest tests/test_live_board.py` |
| **TASK-06** | **P1 (HIGH)** | `web/` | `web/src/components/shell/Sidebar.tsx` | **Implement `isEnterpriseMode` Toggle for Judge Demo**<br>Hide 20 secondary station management routes by default, keeping focus on core 6 ETA forecasting views (Fixes C5). | `cd web && npm run build` |
| **TASK-07** | **P2 (MEDIUM)** | `core` | `requirements.txt` | **Add Missing Dependencies to `requirements.txt`**<br>Add `torch>=2.0.0`, `scipy>=1.10.0`, `PyJWT>=2.8.0`, and `joblib>=1.3.0`. | `pip install -r requirements.txt` |
| **TASK-08** | **P2 (MEDIUM)** | `web/` | `web/src/components/ui/Skeleton.tsx` | **Delete Dead Component `Skeleton.tsx`**<br>Remove unused 15-line component with 0 external imports. | `cd web && npm run build` |
| **TASK-09** | **P2 (MEDIUM)** | `core` | `temp_resultshield/` | **Delete Temporary Benchmark Scratch Directory**<br>Remove 60 unreferenced files in temporary scratch folder. | `git status` |
| **TASK-10** | **P2 (MEDIUM)** | `web/` | `web/src/mock/auth.ts:177` | **Replace Hardcoded URL with `API_BASE`**<br>Replace raw `'http://localhost:8000'` with dynamic environment configuration. | `cd web && npm run build` |
| **TASK-11** | **P2 (MEDIUM)** | `data/` | `data/curated_real_events.csv` | **Remove Duplicate 8.2MB CSV Dataset**<br>Delete redundant CSV file while preserving compressed `curated_real_events.parquet`. | `git status` |
| **TASK-12** | **P3 (LOW)** | `web/` | `web/src/components/landing/ThreeCorridor.tsx` | **Lazy-Load 3D WebGL Landing Canvas**<br>Disable heavy 3D shaders on low-power devices to avoid main thread jank during demo. | `cd web && npm run build` |

---

AUDIT_BASELINE: `d074cc69188948644de72cad7bd4a248547e26ac` | 2026-08-28 | audit-v2.0

