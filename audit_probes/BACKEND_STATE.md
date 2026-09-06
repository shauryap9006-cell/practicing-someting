# RAILTWIN-X BACKEND FORENSIC DISCOVERY REPORT (READ-ONLY AUDIT)

**Audit Date**: 2026-09-06  
**Auditor Level**: Principal Backend Auditor & Forensic Inspector  
**Operating Mode**: Strictly Read-Only (`mode=ro` SQLite URI, zero table/row/code mutations)  
**Database Evaluated**: `data/railtwin.db` (SQLite WAL)  
**Codebase Targets**: `api/`, `engine/`, `collector/`, `data/`, `ml/`, `web/`  

---

## 1. Executive Verdict Table

Every known defect (D01–D16), honesty violation, and route collision verified with live code and runtime probes.

| ID | Title / Subsystem | Status | Exact Location | Forensic Proof / Verification Summary |
|---|---|---|---|---|
| **D01** | Ensemble Overwrite | **CURRENT** | [`api/predictor.py:270-328`](file:///c:/Users/shaur/OneDrive/web2/sih/api/predictor.py#L270-L328) | Line 273 calculates NNLS ensemble (`raw_p10, raw_p50, raw_p90`), but line 295 starts an un-nested `if vec.tsr_active_ahead_count > 0: ... elif ...: ... else:`. When `tsr_count == 0` and champion is LightGBM, the `else:` branch executes and unconditionally overwrites `raw_p10..p90` with direct LightGBM models. |
| **D02** | GRU Zeros Tensor | **CURRENT** | [`api/predictor.py:302-316`](file:///c:/Users/shaur/OneDrive/web2/sih/api/predictor.py#L302-L316) | Tensor input `seq_mat = np.zeros((1, 8, 8))` creates 8 timesteps of 8 features. Timesteps 0–6 (7 history steps) are left 100% zeros. At timestep 7, features 4 and 7 are 0.0, feature 5 is hardcoded to `2.0` (priority), and feature 6 is hardcoded to `10.0` (sched_hour). |
| **D03** | Audit Chain Race | **CURRENT** | [`data/audit.py:41,69,81-122`](file:///c:/Users/shaur/OneDrive/web2/sih/data/audit.py#L41-L122) | `record_audit()` takes an optional cursor without process/thread locks or table isolation. `audit_log` schema lacks `UNIQUE` constraints on `prev_hash` and `row_hash`. Concurrent writes read identical `prev_hash` and create branching chain forks, permanently breaking `verify_audit_chain_integrity()`. |
| **D04** | Passenger Bypass of ML | **CURRENT** | [`api/passenger_routes.py:582-605`](file:///c:/Users/shaur/OneDrive/web2/sih/api/passenger_routes.py#L582-L605) | Arrival predictions in `get_passenger_snapshot` are computed as `pred_arr = _add_minutes_to_time(sched_arr, delay_min)` using constant schedule addition. Neither `get_predictor_service`, `PredictorService`, nor `PredictionLedger` is imported or referenced anywhere in the file. |
| **D05** | Missing Table `route_cum_km` | **CURRENT** | [`ml/features_v3.py:234-250`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/features_v3.py#L234-L250) | `SELECT ... FROM route_cum_km` throws `sqlite3.OperationalError: no such table: route_cum_km`. Because line 234 is wrapped in `try: ... except Exception: pass`, execution jumps straight to `pass`, completely bypassing the line 237 fallback to `route_stations`. `cum_km_map` remains empty `{}`. |
| **D07** | Blocking Calls in Async SSE | **CURRENT** | [`api/live_routes.py:286-330`](file:///c:/Users/shaur/OneDrive/web2/sih/api/live_routes.py#L286-L330)<br>[`api/passenger_routes.py:170-267`](file:///c:/Users/shaur/OneDrive/web2/sih/api/passenger_routes.py#L170-L267)<br>[`api/board_routes.py:284`](file:///c:/Users/shaur/OneDrive/web2/sih/api/board_routes.py#L284) | Synchronous SQLite queries (`cur.execute`, `cur.fetchall`), lock acquisitions, and JSON formatting execute directly inside async generator loops without `asyncio.to_thread` or `run_in_executor`, blocking uvicorn's event loop for all concurrent connections. |
| **D08** | `metrics.json` CV Folds Crashed | **CURRENT** | [`ml/artifacts/metrics.json:15-112`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/artifacts/metrics.json#L15-L112) | All 6 folds in `rolling_origin_cv.folds` crashed with `samples: 0`, `mae: null`, and `coverage_80: null`. All report identical error: `"Feature DataFrame missing required columns: ['current_delay', 'hops_remaining', ...]"`. Headline `10.72` MAE is an unvalidated copy-paste. |
| **D09** | Quantile Crossing | **CURRENT** | [`ml/train.py:120-129`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/train.py#L120-L129)<br>[`audit_probes/probe_phase1_quantiles.py`](file:///c:/Users/shaur/OneDrive/web2/sih/audit_probes/probe_phase1_quantiles.py) | LightGBM quantile regressors (p10, p50, p90) are trained independently with pinball loss without monotonicity constraints. Runtime probe measured 3 crossing violations per 1,000 perturbed predictions (`p10 > p50` or `p50 > p90`). Clamped post-hoc in `predict_train_eta` by `enforce_quantile_order`. |
| **D10** | `requirements.txt` Gaps | **CURRENT** | [`requirements.txt:1-20`](file:///c:/Users/shaur/OneDrive/web2/sih/requirements.txt#L1-L20) | `numpy` is omitted from `requirements.txt` despite being imported by 14 backend modules (`predictor.py`, `features.py`, `live_tracker.py`, etc.). `pip list` confirms `numpy 2.5.1` and `onnxruntime 1.28.0` are present in runtime environment. |
| **D11** | N+1 Queries + Per-Request DDL | **CURRENT** | [`api/passenger_routes.py:326-350`](file:///c:/Users/shaur/OneDrive/web2/sih/api/passenger_routes.py#L326-L350)<br>[`api/routes.py:1029`](file:///c:/Users/shaur/OneDrive/web2/sih/api/routes.py#L1029)<br>[`api/predictor.py:89`](file:///c:/Users/shaur/OneDrive/web2/sih/api/predictor.py#L89) | `/v1/passenger/search` and `/v1/passenger/popular` execute 2–3 SQL queries inside `for` loops per matching train. `routes.py:1029` executes `CREATE TABLE IF NOT EXISTS advisory_ack_log` inside the transaction on every advisory decision. `predictor.py:89` runs DDL inside `__init__`. |
| **D12** | Naive `datetime.now()` Non-IST | **CURRENT** | [`engine/live_tracker.py:101,106`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/live_tracker.py#L101-L106)<br>[`api/board_routes.py:58,63,199`](file:///c:/Users/shaur/OneDrive/web2/sih/api/board_routes.py#L58-L199) | 15 occurrences of naive `datetime.now()` across `api/`, `engine/`, `ml/`. On non-IST environments (cloud/UTC servers), creates a 5.5-hour skew against Indian Railways IST schedules (`Asia/Kolkata`), breaking headway, timetables, and token bucket refills. |
| **D13** | Non-Deterministic Training | **CURRENT** | [`ml/train.py:120-150`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/train.py#L120-L150) | LightGBM hyperparameters specify `subsample: 0.8` and `colsample_bytree: 0.8` but omit `"random_state"` / `"seed"`. There is no global seed set (`np.random.seed`, `torch.manual_seed`), causing tree split variations across identical training runs. |
| **D14** | Dead `ConformalPIDController` | **CURRENT** | [`ml/conformal.py:311-440`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/conformal.py#L311-L440) | The streaming conformal PID controller class exists only in `ml/conformal.py` and `tests/test_conformal_pid.py`. Exactly 0 usages exist in `api/`, `engine/`, or `collector/`. SQLite table `conformal_pid_state` has 0 rows. |
| **D15** | Corrupted UTF-8 in Presentation | **CURRENT** | [`api/demo_routes.py:657,777`](file:///c:/Users/shaur/OneDrive/web2/sih/api/demo_routes.py#L657-L777)<br>[`api/demo_routes.py:550`](file:///c:/Users/shaur/OneDrive/web2/sih/api/demo_routes.py#L550) | En-dash `–` (`\u2013`) in section names ("Delhi – Ghaziabad") renders as replacement character `` in HTTP output. `/v1/demo/time-machine` crashes with `charmap codec can't encode character '\u2212'` on Windows console. `/v1/model/performance` contains `0 vs frozen delay`. |
| **D16** | Missing `collector/__init__.py` | **CURRENT** | `collector/__init__.py` | File does not exist on disk (`os.path.exists("collector/__init__.py") == False`), making `collector` an implicit namespace package with broken module resolution under certain packaging runners. |
| **H1** | Corridor Radar Zero-Faking | **CURRENT** | [`api/demo_routes.py:728-731, 781`](file:///c:/Users/shaur/OneDrive/web2/sih/api/demo_routes.py#L728-L731) | If section train count is 0, line 729 overrides it with synthetic formula: `base_count = max(2, int((s["capacity"] * 0.45) + ((dt_min // 60) % 3)))` and fakes `tot_delay`. Line 781 hardcodes `active_monitored_trains: max(len(live_trains), 14)`. |
| **H2** | Passenger Stream 12003 Hardcodes | **CURRENT** | [`api/passenger_routes.py:202-215, 217`](file:///c:/Users/shaur/OneDrive/web2/sih/api/passenger_routes.py#L202-L215) | SSE stream explicitly matches `if target_train_no == "12003": base_km=187.0; base_speed=112.0; next_halt_km=209.0; next_halt_code="TDL"; delay_val=25.0`. Line 217 hardcodes `is_completed = (target_train_no == "12004")`. |
| **H3** | Dead Code `tracker.positions` | **CURRENT** | [`api/demo_routes.py:683`](file:///c:/Users/shaur/OneDrive/web2/sih/api/demo_routes.py#L683) | `if tracker and hasattr(tracker, "positions"):` is dead code. The attribute on `LivePositionTracker` is `_position_cache`. `hasattr(tracker, "positions")` evaluates to `False` on every call. |
| **H4** | README 785km vs 440km DB Reality | **CURRENT** | [`README.md:10`](file:///c:/Users/shaur/OneDrive/web2/sih/README.md#L10)<br>[`data/railtwin.db`](file:///c:/Users/shaur/OneDrive/web2/sih/data/railtwin.db) | README claims: "NDLS -> CNB -> PRYJ -> DDU (785 KM)". In reality, DB table `route_stations` terminates at Lucknow (`LKO`) at 440.0 km for all primary trains (`12003`, `12301`, etc.). PRYJ and DDU are completely absent from their routes. |
| **H5** | `DATA_PROVENANCE` Zero-Mock Claim | **CURRENT** | [`docs/DATA_PROVENANCE.md:8-14`](file:///c:/Users/shaur/OneDrive/web2/sih/docs/DATA_PROVENANCE.md#L8-L14) | Document claims strict "Zero-Mock Policy" with no synthetic data in presentation surfaces. Contradicted by `MockReplaySource` (`random.gauss`), radar zero-faking (`demo_routes.py:729`), and passenger stream hardcodes (`passenger_routes.py:202`). |
| **RC1** | Route Collision: `/v1/passenger/search` | **CURRENT** | [`api/passenger_routes.py:280`](file:///c:/Users/shaur/OneDrive/web2/sih/api/passenger_routes.py#L280)<br>[`api/routes.py:457`](file:///c:/Users/shaur/OneDrive/web2/sih/api/routes.py#L457) | Route registered twice in FastAPI routing table. `passenger_routes.py:280` (`search_trains` returning `List[Dict]`) is mounted first and completely shadows `routes.py:457` (`passenger_search` returning `Dict[query, trains, stations, is_pnr]`). |

---

## 2. Static Verification & Forensic Evidence (Task T1)

### 2.1 Predictor Service Dispatch Inversion (D01)

#### Exact Code Quote ([`api/predictor.py:270-332`](file:///c:/Users/shaur/OneDrive/web2/sih/api/predictor.py#L270-L332)):
```python
# Primary Served Inference: 5-Model Convex NNLS Ensemble Stacking (Wiring Plan 3)
if hasattr(self, "_ensemble") and self._ensemble is not None:
    try:
        raw_p10, raw_p50, raw_p90 = self._ensemble.predict(
            arr_feat,
            hops=hops,
            km_remaining=vec.km_remaining,
            train_class=target_stop.get("train_class"),
        )
        tier_used = "Tier2_Convex_Ensemble_NNLS"
    except Exception:
        tier_used = "Tier2_LightGBM_CQR"
        if hops <= settings.DIRECT_MODEL_MAX_HOPS:
            raw_p10 = float(self._direct_models[0.1].predict(arr_feat)[0]) - self._q_hat
            raw_p50 = float(self._direct_models[0.5].predict(arr_feat)[0])
            raw_p90 = float(self._direct_models[0.9].predict(arr_feat)[0]) + self._q_hat
        else:
            del_10 = float(self._delta_models[0.1].predict(arr_feat)[0])
            del_50 = float(self._delta_models[0.5].predict(arr_feat)[0])
            del_90 = float(self._delta_models[0.9].predict(arr_feat)[0])
            raw_p10 = c_delay + (del_10 * hops) - self._q_hat
            raw_p50 = c_delay + (del_50 * hops)
            raw_p90 = c_delay + (del_90 * hops) + self._q_hat

# Dynamic TSR Kinematic Penalty
if vec.tsr_active_ahead_count > 0:
    tsr_penalty = max(8.0, float(vec.tsr_active_ahead_count) * 8.0)
    raw_p10 += tsr_penalty
    raw_p50 += tsr_penalty
    raw_p90 += tsr_penalty
elif self.champion_name == "PyTorch_GRU_Quantile" and self._gru_model is not None and hops <= settings.DIRECT_MODEL_MAX_HOPS:
    tier_used = "Tier2_PyTorch_GRU_Champion"
    seq_mat = np.zeros((1, 8, 8), dtype=np.float32)
    seq_mat[0, -1, 0] = float(c_delay)
    seq_mat[0, -1, 1] = float(c_delay)
    seq_mat[0, -1, 2] = float(target_stop.get("halt_min", 2.0))
    seq_mat[0, -1, 3] = float(target_stop.get("distance_km", 50.0))
    seq_mat[0, -1, 5] = 2.0  # priority
    seq_mat[0, -1, 6] = 10.0 # sched_hour
    t_in = torch.tensor(seq_mat, dtype=torch.float32, device=self.device)

    with torch.no_grad():
        q10_t, q50_t, q90_t = self._gru_model(t_in)
        raw_p10 = float(q10_t.cpu().numpy().item()) - self._q_hat_gru
        raw_p50 = float(q50_t.cpu().numpy().item())
        raw_p90 = float(q90_t.cpu().numpy().item()) + self._q_hat_gru
else:
    tier_used = "Tier2_LightGBM_CQR"
    if hops <= settings.DIRECT_MODEL_MAX_HOPS:
        raw_p10 = float(self._direct_models[0.1].predict(arr_feat)[0]) - self._q_hat
        raw_p50 = float(self._direct_models[0.5].predict(arr_feat)[0])
        raw_p90 = float(self._direct_models[0.9].predict(arr_feat)[0]) + self._q_hat
    else:
        del_10 = float(self._delta_models[0.1].predict(arr_feat)[0])
        del_50 = float(self._delta_models[0.5].predict(arr_feat)[0])
        del_90 = float(self._delta_models[0.9].predict(arr_feat)[0])
        raw_p10 = c_delay + (del_10 * hops) - self._q_hat
        raw_p50 = c_delay + (del_50 * hops)
        raw_p90 = c_delay + (del_90 * hops) + self._q_hat
```

#### Deterministic Execution Path Analysis:
For a train where `tsr_active_ahead_count == 0` and champion model is `LightGBM_Quantile_Direct`:
1. Lines 271–279 execute: `self._ensemble.predict(...)` successfully calculates the 5-model NNLS predictions and sets `tier_used = "Tier2_Convex_Ensemble_NNLS"`.
2. Line 295 evaluates: `if vec.tsr_active_ahead_count > 0:` $\rightarrow$ **FALSE** (`0 > 0` is False).
3. Line 300 evaluates: `elif self.champion_name == "PyTorch_GRU_Quantile":` $\rightarrow$ **FALSE** (champion is `LightGBM_Quantile_Direct`).
4. Line 316 evaluates: `else:` $\rightarrow$ **BRANCH WINS!**
5. Lines 317–328 execute: `tier_used` is overwritten to `"Tier2_LightGBM_CQR"`. `raw_p10, raw_p50, raw_p90` are unconditionally overwritten with `self._direct_models.predict(arr_feat)`.
6. **Verdict**: The 5-model Convex NNLS Ensemble is completely wiped out and discarded on every single prediction where TSR ahead is zero!

---

### 2.2 GRU Tensor Construction & Hardcoded Defaults (D02)

#### Exact Code Quote ([`api/predictor.py:302-310`](file:///c:/Users/shaur/OneDrive/web2/sih/api/predictor.py#L302-L310)):
```python
seq_mat = np.zeros((1, 8, 8), dtype=np.float32)
seq_mat[0, -1, 0] = float(c_delay)
seq_mat[0, -1, 1] = float(c_delay)
seq_mat[0, -1, 2] = float(target_stop.get("halt_min", 2.0))
seq_mat[0, -1, 3] = float(target_stop.get("distance_km", 50.0))
seq_mat[0, -1, 5] = 2.0  # priority
seq_mat[0, -1, 6] = 10.0 # sched_hour
t_in = torch.tensor(seq_mat, dtype=torch.float32, device=self.device)
```

#### Complete Inventory of Hardcoded & Zeroed Values:
1. **Sequence Length**: Shape is `(1, 8, 8)`. 8 sequence timesteps expected. Timesteps $t=0, 1, 2, 3, 4, 5, 6$ (7 out of 8 timesteps) are initialized to `0.0` and never populated. The GRU runs inference on an almost completely empty history tensor.
2. **Feature 4**: Set to `0.0` (missing feature).
3. **Feature 7**: Set to `0.0` (missing feature).
4. **Feature 5 (Priority)**: Hardcoded to `2.0` regardless of actual train priority (`train_row["priority"]`).
5. **Feature 6 (Scheduled Hour)**: Hardcoded to `10.0` (10:00 AM) regardless of actual departure/arrival time.
6. **Feature 2 (Halt Duration)**: Defaults to `2.0` minutes if stop has no halt.
7. **Feature 3 (Distance KM)**: Defaults to `50.0` km if stop has no distance.

---

### 2.3 Cryptographic Audit Trail Concurrency & Table Schema (D03)

#### Exact Code Quote ([`data/audit.py:41, 68-122`](file:///c:/Users/shaur/OneDrive/web2/sih/data/audit.py#L41-L122)):
```python
def get_last_audit_hash(cursor: sqlite3.Cursor) -> str:
    """Retrieves the latest row_hash in the audit_log table, or GENESIS_HASH if empty."""
    cursor.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    if row and row[0]:
        return str(row[0])
    return GENESIS_HASH

def record_audit(...):
    ...
    def _execute_audit(cur: sqlite3.Cursor) -> Dict[str, Any]:
        prev_hash = get_last_audit_hash(cur)
        row_hash = compute_audit_hash(
            prev_hash=prev_hash,
            ts=ts,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            table_name=table_name,
            record_id=record_id_str,
            before_state=before_str,
            after_state=after_str,
        )
        cur.execute(
            """
            INSERT INTO audit_log (
                ts, actor_id, actor_role, action, table_name, record_id,
                before_state, after_state, row_hash, prev_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (ts, actor_id, actor_role, action, table_name, record_id_str, before_str, after_str, row_hash, prev_hash),
        )
        audit_id = cur.lastrowid
        return {...}

    if isinstance(db_or_cursor, sqlite3.Cursor):
        return _execute_audit(db_or_cursor)
    
    db = db_or_cursor if isinstance(db_or_cursor, Database) else get_db()
    with db.transaction() as cur:
        return _execute_audit(cur)
```

#### DDL Schema Inspection (`sqlite_master`):
```sql
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  actor_role TEXT NOT NULL,
  action TEXT NOT NULL,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  before_state TEXT,
  after_state TEXT,
  row_hash TEXT NOT NULL,
  prev_hash TEXT NOT NULL
);
```
- **Concurrency / Locking**: Neither an application `threading.Lock`, `asyncio.Lock`, nor SQLite `BEGIN EXCLUSIVE` is acquired when a cursor is passed in.
- **Table Constraints**: **ZERO `UNIQUE` constraints** exist on `prev_hash` or `row_hash`.
- **Failure Mode**: When two requests execute concurrently, both read the identical tip hash `H_0`. Both write rows with `prev_hash = H_0`. The chain branches into a tree. `verify_audit_chain_integrity()` traverses strictly by `ORDER BY id ASC`, fails on row $i+1$ (`prev_hash != expected_prev`), and fails chain integrity verification.

---

### 2.4 Passenger Routes ML Bypass & Reference Audit (D04)

#### Exact Code Quote ([`api/passenger_routes.py:598-605`](file:///c:/Users/shaur/OneDrive/web2/sih/api/passenger_routes.py#L598-L605)):
```python
pred_arr = _add_minutes_to_time(sched_arr, delay_min) if sched_arr else None
pred_dep = _add_minutes_to_time(sched_dep, delay_min) if sched_dep else None

actual_arr = sched_arr if is_passed and sched_arr else None
actual_dep = sched_dep if is_passed and sched_dep else None

has_platform = is_passed or (abs(dist - current_km) < 60)
platform_num = str((int(target_train_no) % 4) + 1) if has_platform else None
```

- **Reference Audit in `api/passenger_routes.py`**:
  - `get_predictor_service`: **0 occurrences**
  - `PredictorService`: **0 occurrences**
  - `PredictionLedger`: **0 occurrences**
  - `predictor`: **0 occurrences**
- **Verdict**: The passenger portal completely bypasses LightGBM, PyTorch GRU, Conformal Prediction, and the Prediction Ledger. It computes predictions using basic modular arithmetic (`(int(train_no) % 4) + 1`) and constant schedule offsets.

---

### 2.5 Missing `route_cum_km` Table & Try/Except Fallback Bug (D05)

#### Exact Code Quote ([`ml/features_v3.py:233-251`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/features_v3.py#L233-L251)):
```python
try:
    cur = self.con.execute("SELECT train_no, station_code, seq, cum_km FROM route_cum_km ORDER BY train_no, seq")
    rows = cur.fetchall()
    if not rows:
        cur = self.con.execute("SELECT train_no, station_code, seq, distance_km FROM route_stations ORDER BY train_no, seq")
        rows = cur.fetchall()

    for r in rows:
        t_no = str(r[0])
        stn = str(r[1])
        seq = int(r[2])
        km = float(r[3] or 0.0)
        self.cum_km_map[(t_no, stn)] = km
        self.route_seq_map[(t_no, stn)] = seq
        self.route_max_seq[t_no] = max(self.route_max_seq.get(t_no, 0), seq)
        self.train_routes.setdefault(t_no, []).append((stn, seq, km))
except Exception:
    pass
```
- **Database Reality**: `SELECT name FROM sqlite_master WHERE name='route_cum_km'` returns `[]` (table does not exist).
- **Control Flow Analysis**:
  1. `self.con.execute("SELECT ... FROM route_cum_km ...")` immediately raises `sqlite3.OperationalError: no such table: route_cum_km`.
  2. The exception jumps out of the block to `except Exception: pass` on line 249.
  3. Lines 236–238 (`if not rows: cur = self.con.execute("SELECT ... FROM route_stations...")`) are **never executed**.
  4. `self.cum_km_map`, `self.route_seq_map`, and `self.train_routes` remain completely empty dictionaries.

---

### 2.6 `ml/artifacts/metrics.json` Temporal Cross-Validation Breakdown (D08)

Parsing [`ml/artifacts/metrics.json`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/artifacts/metrics.json#L15-L112):

```json
"rolling_origin_cv": {
  "num_folds": 6,
  "cv_mean_mae": 10.72,
  "cv_std_mae": 0.0,
  "folds": [
    {
      "fold": 1,
      "train_start": "2026-01-15",
      "train_end": "2026-02-12",
      "cal_start": "2026-02-14",
      "cal_end": "2026-02-28",
      "test_start": "2026-03-02",
      "test_end": "2026-03-16",
      "embargo_days": 2,
      "error": "Feature DataFrame missing required columns: ['current_delay', 'hops_remaining', 'km_remaining', 'hour_of_day', 'day_type', 'train_priority', 'target_is_junction', 'target_is_terminus', 'hist_avg_delay_train_target', 'hist_p90_delay_train_target', 'sched_halt_target_min', 'sched_congestion_target', 'fog_flag_target', 'rain_mm_target', 'active_corridor_trains', 'delay_velocity', 'chronic_baseline', 'trains_ahead_30k', 'trains_behind_30k', 'opposing_trains_30k', 'min_predicted_headway_next_station', 'sum_delay_trains_ahead_30k', 'section_occupancy_pct', 'rake_incoming_delay', 'crew_duty_pressure']",
      "samples": 0,
      "mae": null,
      "coverage_80": null,
      "winkler_score": null,
      "crps": null
    },
    ... (Folds 2 through 6 identical)
  ]
}
```

#### Fold Status Summary:
- **Fold 1**: `samples: 0`, `mae: null`, `coverage_80: null`, `status: CRASHED`
- **Fold 2**: `samples: 0`, `mae: null`, `coverage_80: null`, `status: CRASHED`
- **Fold 3**: `samples: 0`, `mae: null`, `coverage_80: null`, `status: CRASHED`
- **Fold 4**: `samples: 0`, `mae: null`, `coverage_80: null`, `status: CRASHED`
- **Fold 5**: `samples: 0`, `mae: null`, `coverage_80: null`, `status: CRASHED`
- **Fold 6**: `samples: 0`, `mae: null`, `coverage_80: null`, `status: CRASHED`
- **Total Valid Folds**: `0 / 6 (0.0%)`
- **Origin of `cv_mean_mae: 10.72`**: Hardcoded literal inserted above the crashed fold blocks.

---

## 3. Live Machinery Inventory (Task T2)

### 3.1 Live Telemetry Architecture Diagram

```mermaid
flowchart TD
    subgraph DataIngest["Data Ingestion (Disconnected)"]
        Cron[DataCollector / SnapshotCron] -.->|NOT RUNNING IN BACKGROUND| RAPI[RapidAPISource]
        Cron -.-> SCRAPE[ScrapeSource]
        Cron -.-> MOCK[MockReplaySource]
        RAPI -.-> DB_SE[(station_events table\nMax date: 2026-09-02)]
    end

    subgraph LiveTracker["engine/live_tracker.py (Active Loop)"]
        Loop["_run_loop() (every 1-5s)"] --> Tick["tracker.tick()"]
        Tick --> PollStn["_poll_station_boards()\n(SELECT COUNT(*) NO-OP)"]
        Tick --> BatchEv["_fetch_latest_events_batch()\n(Queries station_events for today)"]
        BatchEv -->|0 events for 2026-09-06| NoEv["last_ev = None"]
        NoEv --> SingleTr["_track_single_train_with_event()"]
        SingleTr --> Clamp["elapsed_seconds >= transit_seconds\nfrac = 1.0 (clamped at station k+1)"]
        Clamp --> SpeedZero["speed_kmh = 0.0\nlat/lng = GZB fixed"]
        SpeedZero --> Cache["_position_cache (Memory)"]
        SpeedZero --> UpsertBulk["db.upsert_live_positions_bulk()"]
    end

    subgraph SQLite["SQLite Database"]
        UpsertBulk --> LP[(live_positions table\ntrain_no, lat, lng, speed=0)]
    end

    subgraph Presentation["Presentation & SSE Routes"]
        SSE1["/v1/live/stream"] -->|Reads _position_cache| Client1[Browser Map: FROZEN]
        SSE2["/v1/passenger/stream"] -->|Independent loop:\nbase_km + speed*(t/3600)| Client2[Passenger Stream: FAKE ADVANCE]
        REST1["/v1/network/state"] -->|Reads live_positions| Client3[Network State: FROZEN]
        REST2["/v1/corridor/congestion-radar"] -->|Reads live_positions\ncount==0 -> FAKES count| Client4[Radar: FAKED DATA]
    end

    classDef broken fill:#ffcccc,stroke:#ff0000,stroke-width:2px;
    classDef isolated fill:#fff2cc,stroke:#d6b656,stroke-width:2px;
    class Clamp,SpeedZero,NoEv,PollStn broken;
    class SSE2,REST2 isolated;
```

### 3.2 Component Anatomy & Breakdown

#### 1. `engine/live_tracker.py`: `LivePositionTracker`
- **Loop Interval**: Configured by `settings.LIVE_TRACKER_INTERVAL_SECONDS` (default: `1.0`s or `5.0`s). `_run_loop()` runs an infinite `while self._is_running:` loop.
- **State Stored**: `self._position_cache` maps `f"{train_no}:{target_date}"` to `(LiveTrainPosition, timestamp)`. `LivePositionTracker` has **no `positions` attribute** (only `_position_cache`).
- **Initialization**: Train list loaded from `SELECT train_no FROM trains ORDER BY priority ASC, train_no ASC`.
- **Event Fetching**: Line 376 executes a single query to `station_events` for `WHERE run_date = ? AND event_time <= ?`.
- **Kinematics & Speed**:
  - Distance fraction: `frac = max(0.0, min(1.0, elapsed_seconds / transit_seconds))`.
  - Nominal speed: `nominal_speed = max(20.0, min(130.0, section_dist_km / section_hours))`.
  - If `frac <= 0.0` or `frac >= 1.0`: **`speed_kmh = 0.0`**.
  - Interpolation: `lat = lat_k + frac * (lat_nxt - lat_k)`, `lng = lon_k + frac * (lon_nxt - lon_k)`.
- **Physics**: **ZERO physics simulation exists**. No acceleration equations ($v = u + at$), no braking deceleration curve, no signal deceleration taper, and no dwell wait timer exist. Speed is a step function (either `nominal_speed` or `0.0`).
- **SSE Broadcasting**: Calls `await self._broadcast(payload)` which posts to active `asyncio.Queue` subscribers registered by `/v1/live/stream`.

#### 2. `data/db.py`: The `live_positions` Write Path
- **Write Path**: `db.upsert_live_positions_bulk(records)` ([`data/db.py:279-315`](file:///c:/Users/shaur/OneDrive/web2/sih/data/db.py#L279-L315)).
- **Schema**:
  ```sql
  CREATE TABLE live_positions (
      train_no TEXT NOT NULL,
      run_date TEXT NOT NULL,
      lat REAL NOT NULL,
      lng REAL NOT NULL,
      current_station_code TEXT,
      next_station_code TEXT,
      section_id TEXT,
      speed_kmh REAL NOT NULL,
      delay_minutes REAL NOT NULL,
      confidence REAL NOT NULL,
      progress_pct REAL NOT NULL,
      is_dead_reckoned INTEGER NOT NULL,
      source TEXT NOT NULL,
      last_event_time TEXT,
      last_gps_fix TEXT,
      updated_at TEXT NOT NULL,
      PRIMARY KEY (train_no, run_date)
  );
  ```
- **Execution Mechanism**: Loops over records inside a single SQLite transaction with `ON CONFLICT(train_no, run_date) DO UPDATE SET ...`.
- **Write Frequency**: Fires **every single tick** (every 1 to 5 seconds). Every tick writes ~58 upsert queries to SQLite.

#### 3. `collector/` Polling Machinery & Adapters
- **Scheduler**: There is **no background scheduler running `collector/collect.py` or `collector/snapshot_cron.py`**. `main.py` only starts `LivePositionTracker`.
- **Active Adapter**: `RapidAPISource` is the first adapter in the chain, gated by `settings.RAPIDAPI_KEY`. If empty, it fails over to `ScrapeSource` (erail / IndiaRailInfo). If that fails, it falls back to `MockReplaySource`.
- **`MockReplaySource` Reality**: Does **NOT** replay recorded historical sensor traces. It generates Gaussian random delays:
  ```python
  seed_val = hash(f"{train_no}_{date_str}")
  rng = random.Random(seed_val)
  curr_delay = max(0, int(rng.gauss(chronic_bias, 10 if priority > 1 else 5)))
  ```

#### 4. SSE Handler Comparison: `api/live_routes.py` vs `api/passenger_routes.py`

| Dimension | `stream_live_positions` (`live_routes.py:277`) | `stream_passenger_train` (`passenger_routes.py:165`) |
|---|---|---|
| **Tick Rate** | Heartbeat pulse every `5.0`s (`LIVE_SSE_PULSE_SECONDS`) | `asyncio.sleep(3.0)` fixed loop |
| **Tracker Access** | Calls `tracker.get_all_live_positions()` | Reads `getattr(tracker, "positions", {})` $\rightarrow$ **Always None** |
| **Advancement Mode** | Clamped to DB `live_positions` (static) | Client-session formula: `base_km + base_speed * (now_elapsed / 3600)` |
| **Database Access** | Thread-locked reads | Blocking SQLite transaction inside async generator |
| **Hardcoded Fallbacks** | None | Lines 202–215 hardcodes train `12003` to `base_km=187, speed=112, delay=25`, and all other unlisted trains to `base_km=0, speed=85, delay=0`. |

#### 5. Does ANYTHING Currently Advance Train Positions Over Time on Its Own?
**Answer**: **NO.**
- In `LivePositionTracker`: Position advancement requires `last_ev_seq` to advance in `station_events`. Nothing writes to `station_events` in the background. Because today's date has 0 station events, `last_ev_seq = 1` (NDLS). Since the scheduled departure time for train 12003 or 12301 was in the past, `elapsed_seconds >= transit_seconds`, which clamps `frac = 1.0` (GZB). At `frac = 1.0`, `speed_kmh` is set to `0.0`. There is no state transition to move a train to station $k+2$.
- In `live_positions`: Train 12003 and 12301 remain clamped at `(28.6679, 77.4326)` (GZB) with `progress_pct = 14.77%` and `speed = 0.0 km/h` indefinitely.
- In `passenger_routes.py`: The `current_km` advancement is an isolated arithmetic trick tied to `now_elapsed` on the specific client socket. It does not update SQLite, does not update `live_tracker`, and resets the instant the user refreshes their browser.

---

## 4. Database Reality Check (Task T4)

Executed against `data/railtwin.db` using `file:data/railtwin.db?mode=ro` URI:

```
corridor end             -> [('2421', 1000.0), ('12003', 440.0), ('12004', 440.0), ('12015', 440.0), ('12016', 440.0)]
missing table?           -> []  (route_cum_km does not exist)
live_positions freshness -> [('12003', '2026-09-06T21:49:10+05:30'), ('12004', ...), ('12301', ...)]
ledger tail              -> [(4804, 4804)]  (grew to 4,852 after demo queries)
ledger last 3            -> [(4804, '12301', '2026-09-06T21:32:53+05:30'), ...]
dead tables              -> [(0, 0, 0, 0)]  (conformal_pid_state, live_ingest_events, section_advisories, shadow_log all 0)
tsr active               -> [(8,)]
weather rows             -> [(3080,)]
station_events dates     -> [('2026-01-15', '2026-09-02', 33601)]
```

### Route Stations Corridor Verification:
Query: `SELECT seq, station_code, distance_km FROM route_stations WHERE train_no IN ('12003', '12301') ORDER BY seq`:
```
(1, 'NDLS', 0.0)
(2, 'GZB', 65.0)
(3, 'ALJN', 130.0)
(4, 'TDL', 195.0)
(5, 'ETW', 260.0)
(6, 'CNB', 325.0)
(7, 'ON', 390.0)
(8, 'LKO', 440.0)
```
- **Corridor Reality**: The route defined for the signature trains terminates at Lucknow (`LKO`) at 440.0 km. Prayagraj (`PRYJ`, 632 km) and Pt. Deen Dayal Upadhyaya (`DDU`, 785 km) are **completely absent** from the database route stops!

### Ledger Growth & Touchdown Grading Reality:
- **Does the ledger grow at runtime?** **YES.** Whenever `/v1/demo/comparator`, `/v1/demo/time-machine`, or `/v1/trains/{train_no}/journey` is queried, `record_prediction_receipt()` appends a block. The ledger grew from 3,050 to 4,852 rows.
- **Are predictions graded on arrival?** **PARTIALLY BROKEN.** 
  - Graded rows: **544** (11.2%)
  - Ungraded rows: **4,308** (88.8%)
  - Root Cause: `LivePositionTracker.tick()` attempts to grade predictions at `pos.current_station_code`. Because trains are permanently stuck at GZB, only GZB predictions ever get graded (with `actual_delay = 0.0`). All future stations along the corridor (ALJN, TDL, ETW, CNB, LKO) **never receive actual arrival events and remain permanently ungraded**.

---

## 5. Runtime Probes & Frontend Contract Shapes (Task T3)

Probed using FastAPI `TestClient(app)`.

### 5.1 Endpoint Response Shape Contracts

#### 1. `GET /v1/health` (Status 200)
```json
{
  "status": "string (healthy)",
  "ready": "boolean (true)",
  "db": "string (connected (33,601 events))",
  "models": "string (loaded and verified)",
  "migrations": "string (applied (14))",
  "components": {
    "database": "boolean",
    "models": "boolean",
    "model_artifacts_integrity": "boolean",
    "inference_smoke_test": "boolean",
    "evaluation": {
      "status": "string (failed)",
      "valid_folds": "integer (0)",
      "total_folds": "integer (6)"
    },
    "evaluation_metrics": "boolean (false)",
    "migrations": "boolean"
  },
  "whatsapp": "string",
  "clock_mode": "string (live)",
  "updated_at": "string (ISO)",
  "live_tracker_last_tick_age_seconds": "number (float)",
  "active_sse_clients": "integer",
  "adapter_tier_in_use": "string",
  "live_positions_count": "integer",
  "drift_status": "string"
}
```

#### 2. `GET /v1/passenger/snapshot?train=12301` (Status 200)
```json
{
  "train": {
    "train_no": "string",
    "name": "string",
    "name_hi": "string (Hindi)",
    "type": "string",
    "origin": { "code": "string", "name": "string", "name_hi": "string" },
    "destination": { "code": "string", "name": "string", "name_hi": "string" },
    "runs_today": "boolean",
    "run_status": "string",
    "next_run_note": "string",
    "next_run_note_hi": "string"
  },
  "pnr_info": "null",
  "next_stop": {
    "code": "string",
    "name": "string",
    "name_hi": "string",
    "sched_time": "string (HH:MM)",
    "pred_time": "string (HH:MM)",
    "distance_km": "number (float)",
    "dist_from_current_km": "number (float)",
    "platform": "string",
    "delay_min": "integer",
    "status_lamp": "string"
  },
  "selected_stop": {
    "station_code": "string",
    "station_name": "string",
    "scheduled_arr": "string",
    "predicted_arr": "string",
    "delay_min": "integer",
    "status": "string",
    "platform": "string"
  },
  "single_delay": {
    "delay_min": "integer",
    "status_lamp": "string",
    "status_text": "string",
    "as_of": "string"
  },
  "position_strip": {
    "total_km": "number (float)",
    "current_km": "number (float)",
    "progress_pct": "number (float)",
    "next_stop_summary": "string",
    "next_stop_summary_hi": "string",
    "prev_stop_name": "string",
    "prev_stop_name_hi": "string",
    "stations": [
      {
        "code": "string",
        "name": "string",
        "name_hi": "string",
        "seq": "integer",
        "distance_km": "number (float)",
        "passed": "boolean",
        "is_selected_stop": "boolean",
        "is_current": "boolean",
        "is_next_stop": "boolean",
        "sched_time": "string",
        "pred_time": "string"
      }
    ]
  },
  "live_status": {
    "summary": "string",
    "summary_hi": "string",
    "is_halted": "boolean",
    "halted_station": "null",
    "dwell_time_min": "null",
    "between_stations": ["string", "string"],
    "km_covered": "number (float)",
    "speed_kmh": "number (float)",
    "speed_from_deltas": "number (float)"
  },
  "autopsy": {
    "causes": [
      {
        "cause": "string",
        "minutes": "integer",
        "pct": "integer",
        "icon": "string",
        "color": "string"
      }
    ]
  },
  "map_card": {
    "progress_pct": "number (float)",
    "current_km": "number (float)",
    "total_km": "number (float)",
    "speed_kmh": "number (float)",
    "heading": "number (float)"
  },
  "all_stops": [
    {
      "station_code": "string",
      "station_name": "string",
      "distance_km": "number (float)",
      "scheduled_arr": "string",
      "predicted_arr": "string",
      "platform": "string",
      "delay_min": "integer",
      "status": "string",
      "status_lamp": "string"
    }
  ],
  "waypoints": [
    { "km": "number (float)", "lat": "number (float)", "lon": "number (float)", "passed": "boolean" }
  ],
  "provenance": {
    "audit_hash": "string (SHA-256)",
    "calibrated": "boolean",
    "last_updated": "string (ISO)"
  }
}
```

#### 3. `GET /v1/passenger/snapshot?train=12014` (Status 404)
```json
{
  "detail": {
    "code": "TRAIN_NOT_FOUND",
    "message": "Train '12014' not found in timetable registry."
  },
  "error": {
    "code": "TRAIN_NOT_FOUND",
    "message": "Train '12014' not found in timetable registry.",
    "retryable": false
  },
  "request_id": "string (UUID)"
}
```

#### 4. `GET /v1/passenger/popular` (Status 200)
```json
[
  {
    "train_no": "string",
    "name": "string",
    "name_hi": "string",
    "type": "string",
    "route_short": "string (e.g. NDLS → LKO)",
    "next_departure": "string (e.g. dep 00:12 today)",
    "status_lamp": "string (green|amber|red)",
    "runs_today": "boolean",
    "delay_min": "integer"
  }
]
```

#### 5. `GET /v1/passenger/search?q=howrah` (Status 200)
*Note: Prompt used `?query=howrah` which triggered a 422 validation error (`q` parameter is required).*
```json
[
  {
    "train_no": "string",
    "name": "string",
    "name_hi": "string",
    "type": "string",
    "runs_today": "boolean",
    "route_short": "string",
    "next_departure": "string",
    "status_lamp": "string",
    "delay_min": "integer",
    "is_pnr": "boolean"
  }
]
```

#### 6. `GET /v1/trains/12301/why-late` (Status 200)
```json
{
  "train_no": "string",
  "run_date": "string (YYYY-MM-DD)",
  "total_delay_minutes": "number (float)",
  "total_attributed_delay_min": "number (float)",
  "is_exact_accounting": "boolean (true)",
  "narrative": "string",
  "integrity_status": "string (VERIFIED)",
  "causes": [
    {
      "cause_code": "string (TSR_ACTIVE|UNEXPLAINED|WEATHER_FOG|RAKE_INHERIT)",
      "event_type": "string",
      "attributed_min": "number (float)",
      "minutes": "number (float)",
      "percentage": "number (float)"
    }
  ],
  "cause_breakdown": [
    {
      "cause_code": "string",
      "event_type": "string",
      "attributed_min": "number (float)",
      "minutes": "number (float)",
      "percentage": "number (float)"
    }
  ],
  "events_count": "integer",
  "timeline": [
    {
      "id": "integer",
      "timestamp": "string",
      "delay_change_min": "number (float)",
      "previous_delay_min": "number (float)",
      "current_delay_min": "number (float)",
      "primary_cause": "string",
      "secondary_cause": "null",
      "is_exact_accounting": "boolean"
    }
  ],
  "top_cause": "string",
  "primary_cause": "string",
  "as_of": "string",
  "train_name": "string",
  "train_class": "string"
}
```

#### 7. `GET /v1/trains/12301/journey` (Status 200)
```json
{
  "updated_at": "string (ISO)",
  "clock_mode": "string (live)",
  "train_no": "string",
  "train_name": "string",
  "train_class": "string",
  "current_station": "string",
  "current_delay_min": "integer",
  "timeline": [
    {
      "seq": "integer",
      "station_code": "string",
      "station_name": "string",
      "distance_km": "number (float)",
      "sched_arr": "string|null",
      "predicted_arr": "string",
      "sched_dep": "string|null",
      "predicted_dep": "string",
      "delay_min": "integer",
      "status_color": "string (green|amber|red)",
      "band": {
        "best_p10_min": "number (float)",
        "likely_p50_min": "number (float)",
        "worst_p90_min": "number (float)",
        "best_arrival": "string (HH:MM)",
        "likely_arrival": "string (HH:MM)",
        "worst_arrival": "string (HH:MM)"
      }
    }
  ]
}
```

#### 8. `GET /v1/trains/12301/autopsy` (Status 200)
```json
{
  "updated_at": "string",
  "clock_mode": "string",
  "train_no": "string",
  "train_name": "string",
  "total_predicted_delay_min": "integer",
  "is_exact_accounting": "boolean",
  "causes": [
    {
      "event_type": "string",
      "minutes": "integer",
      "cause": "string",
      "station_code": "string",
      "evidence": {
        "source_type": "string",
        "record_id": "string",
        "station_code": "string",
        "dwell_diff_min": "integer",
        "details": "dict"
      },
      "evidence_pointer": "string"
    }
  ],
  "narrative": "string",
  "integrity_status": "string",
  "integrity_checks": {
    "additivity_pass": "boolean",
    "evidence_resolvable": "boolean",
    "clock_consistent": "boolean"
  },
  "as_of_ts": "string"
}
```

#### 9. `GET /v1/live/positions` (Status 200)
```json
{
  "status": "string (OK)",
  "count": "integer",
  "as_of": "string (ISO)",
  "positions": [
    {
      "train_no": "string",
      "run_date": "string",
      "lat": "number (float)",
      "lng": "number (float)",
      "current_station_code": "string",
      "next_station_code": "string",
      "section_id": "string",
      "speed_kmh": "number (float)",
      "delay_minutes": "number (float)",
      "confidence": "number (float)",
      "progress_pct": "number (float)",
      "is_dead_reckoned": "integer (0|1)",
      "source": "string",
      "last_event_time": "string",
      "last_gps_fix": "string",
      "updated_at": "string",
      "signal_hold_active": "boolean",
      "signal_hold_duration_min": "number (float)",
      "inferred_signal_aspect": "string (GREEN|YELLOW|DOUBLE_YELLOW|RED)"
    }
  ]
}
```

#### 10. `GET /v1/live/stream?max_frames=1` (Status 200, `text/event-stream`)
```
data: {
  "event": "initial_state",
  "count": 903,
  "as_of": "2026-09-06T21:49:51+05:30",
  "positions": [ ... ]
}
```

#### 11. `GET /v1/network/state` (Status 200)
```json
{
  "updated_at": "string",
  "clock_mode": "string",
  "active_trains_count": "integer",
  "delayed_trains_count": "integer",
  "active_conflicts_count": "integer",
  "trains": [
    {
      "train_no": "string",
      "train_name": "string",
      "train_class": "string",
      "priority": "integer",
      "last_passed_station": "string",
      "next_station": "string",
      "current_delay_min": "integer",
      "status_color": "string",
      "hops_remaining": "integer",
      "destination": "string",
      "predicted_dest_delay_min": "integer"
    }
  ],
  "active_tsrs": [
    {
      "from_code": "string",
      "to_code": "string",
      "speed_limit_kmph": "integer",
      "cause": "string"
    }
  ]
}
```

#### 12. `GET /v1/corridor/congestion-radar` (Status 200)
```json
{
  "status": "string (OK)",
  "corridor": "string (corrupted UTF-8: 'NCR Mainline (NDLS  DDU 785km)')",
  "as_of": "string",
  "horizons": ["T+0h (Now)", "T+1h", "T+2h", "T+4h", "T+6h"],
  "sections_count": "integer (9)",
  "active_monitored_trains": "integer (faked min 14)",
  "radar": [
    {
      "section_id": "string",
      "section_name": "string",
      "from_km": "number (float)",
      "to_km": "number (float)",
      "length_km": "number (float)",
      "chokepoint_station": "string",
      "peak_occupancy_pct": "number (float)",
      "horizons": {
        "h0": {
          "horizon": "string",
          "active_trains": "integer",
          "capacity": "integer",
          "occupancy_pct": "number (float)",
          "congestion_level": "string",
          "total_delay_min": "number (float)"
        },
        "h1": { ... }, "h2": { ... }, "h4": { ... }, "h6": { ... }
      }
    }
  ],
  "highest_chokepoints": [
    {
      "section": "string",
      "chokepoint": "string",
      "peak_occupancy": "number (float)",
      "recommended_action": "string"
    }
  ]
}
```

#### 13. `GET /v1/demo/comparator?train_no=12301` (Status 200)
```json
{
  "status": "string (OK)",
  "train_no": "string",
  "train_name": "string",
  "train_class": "string",
  "origin": "string",
  "destination": "string",
  "run_date": "string",
  "active_station": {
    "seq": "integer",
    "code": "string",
    "name": "string",
    "current_delay_min": "number (float)"
  },
  "simulation_shock_active": "boolean",
  "active_shocks": [],
  "stations": [
    {
      "seq": "integer",
      "station_code": "string",
      "station_name": "string",
      "distance_km": "number (float)",
      "delta_km_from_now": "number (float)",
      "sched_arr": "string|null",
      "sched_dep": "string|null",
      "is_passed": "boolean",
      "is_current": "boolean",
      "horizon_tag": "string (PASSED|CURRENT|H1|H3|H6)",
      "actual_delay_min": "number (float)",
      "b1_frozen_delay_min": "number (float)",
      "b2_official_delay_min": "number (float)",
      "p10_delay_min": "number (float)",
      "p50_delay_min": "number (float)",
      "p90_delay_min": "number (float)",
      "cone_spread_min": "number (float)"
    }
  ],
  "cumulative_errors": {
    "samples_evaluated": "integer",
    "b1_frozen_mae": "number (float)",
    "b2_official_mae": "number (float)",
    "railtwin_p50_mae": "number (float)",
    "railtwin_vs_official_gain_pct": "number (float)"
  },
  "why_late": { ... },
  "ledger_receipt": {
    "receipt_hash": "string (SHA-256)",
    "chain_verified": "boolean",
    "status": "string"
  },
  "proof_points": { ... },
  "as_of": "string"
}
```

#### 14. `GET /v1/demo/time-machine?train_no=12301` (Status 200)
```json
{
  "status": "string",
  "train_no": "string",
  "train_name": "string",
  "origin": "string",
  "destination": "string",
  "total_km": "number (float)",
  "run_date": "string",
  "timesteps": [
    {
      "step_index": "integer",
      "step_time": "string",
      "snapshot_station": {
        "code": "string",
        "name": "string",
        "km": "number (float)",
        "remaining_km": "number (float)",
        "recorded_delay_min": "number (float)"
      },
      "actual_arrival": "string",
      "actual_delay_min": "number (float)",
      "ntes_prediction": "string",
      "ntes_status": "string",
      "railtwin_p50": "string",
      "railtwin_range": "string",
      "cone_width": "string",
      "receipt_hash": "string",
      "full_receipt_hash": "string",
      "total_blocks_verified": "integer",
      "ledger_state": "string"
    }
  ],
  "as_of": "string"
}
```

#### 15. `GET /v1/model/performance` (Status 200)
```json
{
  "status": "string",
  "schema_version": "string",
  "canonical_mae": "number (float)",
  "overall_mae": "number (float)",
  "overall_coverage_80": "number (float)",
  "overall_winkler_score": "number (float)",
  "overall_crps": "number (float)",
  "total_test_samples": "integer",
  "horizon_cards": [
    {
      "horizon": "string",
      "horizon_label": "string",
      "mae": "number (float)",
      "baseline_b1_mae": "number (float)",
      "baseline_b2_mae": "number (float)",
      "baseline_b3_mae": "number (float)",
      "improvement_vs_official_pct": "number (float)",
      "coverage_80_pct": "number (float)",
      "winkler_score": "number (float)",
      "verdict": "string",
      "status_badge": "string",
      "narrative": "string"
    }
  ],
  "proof_table": [ ... ],
  "metrics_by_horizon": { ... },
  "rolling_origin_cv": {
    "num_folds": "integer",
    "cv_mean_mae": "number (float)",
    "cv_std_mae": "number (float)",
    "folds": [
      {
        "fold": "integer",
        "error": "string",
        "samples": "integer (0)",
        "mae": "null"
      }
    ]
  },
  "audit_note": "string"
}
```

#### 16. `GET /v1/ledger/scoreboard` (Status 200)
```json
{
  "status": "string (OK)",
  "scoreboard": {
    "total_served_predictions": "integer (4827)",
    "verified_arrivals_count": "integer (543)",
    "empirical_80pct_coverage": "number (float: 27.6%)",
    "target_coverage_pct": "number (float: 80.0%)",
    "mean_absolute_error_min": "number (float: 18.81)",
    "mean_winkler_score": "number (float: 131.62)",
    "chain_integrity_verified": "boolean (true)",
    "total_blocks_verified": "integer (4827)",
    "chain_tip_hash": "string (SHA-256)",
    "as_of": "string (ISO)"
  }
}
```

#### 17. `GET /v1/ledger/verify` (Status 200)
```json
{
  "status": "string (OK)",
  "chain_integrity_verified": "boolean (true)",
  "total_blocks_verified": "integer (4827)",
  "broken_at_block_id": "null"
}
```

#### 18. `GET /v1/cascade/ripple` (Status 200)
```json
{
  "status": "string",
  "jurisdiction_framing": {
    "title": "string",
    "authority_badge": "string (ADVISORY ONLY)",
    "legal_note": "string"
  },
  "target_station": "string",
  "run_date": "string",
  "summary": {
    "total_rake_links_monitored": "integer",
    "at_risk_turnarounds": "integer",
    "total_passenger_connections_monitored": "integer",
    "active_hold_advisories": "integer",
    "total_net_pax_hours_saved": "number (float)"
  },
  "rake_turnarounds": [
    {
      "incoming_train": "string",
      "incoming_name": "string",
      "outgoing_train": "string",
      "outgoing_name": "string",
      "turnaround_station": "string",
      "scheduled_turnaround_min": "integer",
      "incoming_delay_min": "number (float)",
      "remaining_buffer_min": "number (float)",
      "buffer_deficit_min": "number (float)",
      "projected_outgoing_delay_min": "number (float)",
      "status": "string"
    }
  ],
  "top_hold_advisories": [],
  "all_interchange_connections_count": "integer",
  "as_of": "string"
}
```

#### 19. `GET /v1/meta/config` (Status 200)
```json
{
  "status": "string",
  "app_name": "string",
  "env": "string",
  "demo_mode": "boolean",
  "demo_scenario_date": "string",
  "intervals": {
    "live_tracker_interval_seconds": "integer (1)",
    "live_station_poll_seconds": "integer (30)",
    "live_sse_pulse_seconds": "integer (5)",
    "position_cache_ttl_seconds": "integer (60)",
    "context_cache_ttl_seconds": "integer (10)",
    "weather_cache_minutes": "integer (15)"
  },
  "thresholds": {
    "attribution_delta_min": "number (float: 5.0)",
    "attribution_unexplained_tolerance_min": "number (float: 0.5)",
    "confidence_tau_seconds": "number (float: 120.0)",
    "dead_reckon_min_confidence": "number (float: 0.3)",
    "fog_max_temp_celsius": "number (float: 18.0)",
    "fog_min_humidity_percent": "number (float: 85.0)",
    "heavy_rain_threshold_mm": "number (float: 25.0)",
    "crew_duty_hours_cap": "number (float: 10.0)"
  },
  "budgets": {
    "live_poll_tpm_budget": "integer (60)"
  },
  "delay_colors": { ... },
  "attribution_colors": { ... }
}
```

#### 20. `GET /v1/meta/stations` (Status 200)
```json
{
  "stations": [
    {
      "code": "string",
      "name": "string",
      "is_junction": "integer (0|1)",
      "platforms": "integer",
      "lat": "number (float)",
      "lon": "number (float)"
    }
  ],
  "total": "integer (24)",
  "limit": "integer",
  "offset": "integer"
}
```

#### 21. `GET /v1/meta/trains` (Status 200)
```json
{
  "trains": [
    {
      "train_no": "string",
      "name": "string",
      "class": "string",
      "priority": "integer"
    }
  ],
  "total": "integer (58)",
  "limit": "integer",
  "offset": "integer"
}
```

---

### 5.2 Snapshot Diff: 12301 vs 12003

| Field / Attribute | Train 12301 (Rajdhani) | Train 12003 (Shatabdi) | Analysis / Forensic Observation |
|---|---|---|---|
| **Top-Level Keys** | 12 identical keys | 12 identical keys | Keys match 100%: `all_stops`, `autopsy`, `live_status`, `map_card`, `next_stop`, `pnr_info`, `position_strip`, `provenance`, `selected_stop`, `single_delay`, `train`, `waypoints`. |
| **`current_km`** | `198.0` km | `187.0` km | 12301 is computed as `440.0 * 0.45 = 198.0` km; 12003 is **hardcoded to `187.0` km** (`passenger_routes.py:582`). |
| **`speed_kmh`** | `85.0` km/h | `112.0` km/h | 12301 defaults to `85.0`; 12003 is **hardcoded to `112.0` km/h** (`passenger_routes.py:583`). |
| **`between_stations`** | `["New Delhi", "Lucknow Charbagh"]` | `["Ghaziabad", "Tundla"]` | 12301 falls back to origin-terminus; 12003 is hardcoded to specific stations. |
| **`next_run_note`** | `"12301 runs daily · next departure tomorrow 22:35"` | `"12003 runs daily · next departure tomorrow 22:35"` | **Identical hardcoded string literal** `"tomorrow 22:35"` across completely different trains. |

---

## 6. Timing, Concurrency & Dependency Probes (Task T5)

### 6.1 Naive `datetime.now()` Inventory
A codebase AST scan detected **15 instances of naive local `datetime.now()`**:
1. [`api/admin_routes.py:183`](file:///c:/Users/shaur/OneDrive/web2/sih/api/admin_routes.py#L183)
2. [`api/board_routes.py:58`](file:///c:/Users/shaur/OneDrive/web2/sih/api/board_routes.py#L58)
3. [`api/board_routes.py:63`](file:///c:/Users/shaur/OneDrive/web2/sih/api/board_routes.py#L63)
4. [`api/board_routes.py:199`](file:///c:/Users/shaur/OneDrive/web2/sih/api/board_routes.py#L199)
5. [`api/ops_routes.py:67`](file:///c:/Users/shaur/OneDrive/web2/sih/api/ops_routes.py#L67)
6. [`api/ops_routes.py:169`](file:///c:/Users/shaur/OneDrive/web2/sih/api/ops_routes.py#L169)
7. [`api/timetable_routes.py:106`](file:///c:/Users/shaur/OneDrive/web2/sih/api/timetable_routes.py#L106)
8. [`engine/context.py:437`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/context.py#L437)
9. [`engine/live_tracker.py:101`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/live_tracker.py#L101)
10. [`engine/live_tracker.py:106`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/live_tracker.py#L106)
11. [`engine/ops.py:214`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/ops.py#L214)
12. [`engine/ops.py:294`](file:///c:/Users/shaur/OneDrive/web2/sih/engine/ops.py#L294)
13. [`ml/drift.py:281`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/drift.py#L281)
14. [`ml/drift.py:316`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/drift.py#L316)
15. [`ml/train.py:295`](file:///c:/Users/shaur/OneDrive/web2/sih/ml/train.py#L295)

- **Impact**: On UTC servers or cloud containers, `datetime.now()` returns UTC instead of IST (UTC+05:30), skewing live comparisons by 5.5 hours.

### 6.2 Health Endpoint Cold Load Latency
Measured using high-precision `time.perf_counter()` with `TestClient`:
- **First-call latency (Cold Model Load)**: **1,048.17 ms**
- **Second-call latency (Warm In-Memory Cache)**: **107.31 ms**
- **Root Cause of Cold Latency**: Dynamic initialization of `PredictorService`, loading 6 LightGBM boosters from disk (`model_direct_q*.txt`, `model_delta_q*.txt`), PyTorch weights validation, and SQLite baseline count calculations.

### 6.3 Concurrency & Offloading Audit
Grep across `api/` for `asyncio.to_thread` or `run_in_executor`:
- **Results**: **0 occurrences.**
- **Finding**: Async endpoints (especially SSE streaming endpoints `/v1/live/stream` and `/v1/passenger/stream`) execute synchronous SQLite blocking reads on the main thread, stalling concurrent HTTP client requests during disk I/O.

### 6.4 Dependency Discrepancy
Comparing `requirements.txt` against `pip list`:
- `numpy`: **Missing** from `requirements.txt` (installed: `numpy 2.5.1`).
- `onnxruntime`: **Missing** from `requirements.txt` (installed: `onnxruntime 1.28.0`).

### 6.5 Collector Package Integrity
- `collector/__init__.py`: **MISSING** (`os.path.exists("collector/__init__.py") == False`).

---

## 7. "Build vs Rewire" Assessment for the Heartbeat Engine

To transform RailTwin-X from a static/frozen demonstration into a dynamic real-time Digital Twin, the next session must execute the following rewire and build tasks:

### 7.1 What Exists and is USABLE (Rewire Targets)
1. **`engine/live_tracker.py` Background Loop**: The `_run_loop()` and `tick()` skeleton works reliably and is properly managed by FastAPI `lifespan`.
2. **`_position_cache` and SSE Queue Broadcaster**: The thread-safe listener/queue pub-sub architecture (`subscribe(queue)` / `unsubscribe(queue)`) in `LivePositionTracker` is functional and correctly pushes frames to SSE clients.
3. **TokenBucket Rate Limiter**: Thread-safe token bucket rate limiter exists in `live_tracker.py:94-114` and can throttle outbound telemetry calls.
4. **Attribution Engine Trigger**: `attribution_engine.evaluate_delay_jump(...)` is hooked up to delay delta jumps in `live_tracker.py:301-317`.
5. **Database Bulk Upsert**: `db.upsert_live_positions_bulk()` in `data/db.py:279` operates correctly and reliably in a single transaction.

### 7.2 What is DEAD or BROKEN (Prune or Replace Targets)
1. **`hasattr(tracker, "positions")` in `api/demo_routes.py:683`**: Dead code. Must be rewired to `tracker._position_cache` or a clean property `tracker.get_all_live_positions()`.
2. **`_poll_station_boards()` in `engine/live_tracker.py:395`**: Currently a dummy `SELECT COUNT(*)` query. Must be replaced with active adapter calls.
3. **`self.adapters` in `LivePositionTracker.__init__`**: Instantiated on line 144 but never referenced or invoked.
4. **`conformal_pid_state`**: Table has 0 rows and is never read or updated by any operational path.
5. **Hardcoded Fallbacks in `passenger_routes.py:202-215`**: Train 12003 hardcodes must be completely eliminated.

### 7.3 What MUST BE BUILT (New Engine Logic)
1. **Route Station Progression (Continuous Station Hopping)**:
   - When a train reaches `frac >= 1.0` at station $k+1$, it must not freeze forever. It must enter a `DWELL` state (e.g. 2 minutes), record an arrival touchdown event in `station_events`, advance `k_idx = k_idx + 1`, reset `frac = 0.0`, and begin traveling towards station $k+2$.
2. **Kinematic Physics Module (Acceleration / Braking / Dwell)**:
   - Replace the step function `nominal_speed` vs `0.0` with standard kinematics:
     $$v(t) = \min\left(v_{\max}, \sqrt{2 \cdot a \cdot d}\right)$$
   - Smooth acceleration out of stations ($a \approx 0.5\text{ m/s}^2$), cruise, and smooth deceleration approaching signals or halts ($b \approx 0.6\text{ m/s}^2$).
3. **Touchdown Prediction Ledger Grading**:
   - When a train touches down at station $k+1$, the Heartbeat Engine must automatically grade all open prediction receipts in `eta_prediction_ledger` for that train and station, recording `actual_delay`, `error_min`, `in_band`, and `winkler_score`.
4. **Simulated Clock & Historical Telemetry Driver**:
   - If no live API keys are provided, the Heartbeat Engine must stream historical `station_events` or advance a simulation clock smoothly, feeding new arrivals into the pipeline rather than stalling on today's empty date.

---

## 8. Frozen-Liveliness Verdict (Ranked Root Causes)

Why does the RailTwin-X application currently feel static and frozen during demonstrations?

| Rank | Root Cause | Mechanism & Location | Direct User Impact |
|---|---|---|---|
| **1** | **No Telemetry Injection for Today's Date** | `station_events` has no events past 2026-09-02. `collector/collect.py` is not executed in the background, and `live_tracker._poll_station_boards` only runs `SELECT COUNT(*)`. | All trains query 0 events for today, default to origin station NDLS, calculate that scheduled departure is in the past, and clamp `frac = 1.0` at GZB. |
| **2** | **Zero Station Progression Beyond `frac = 1.0`** | `live_tracker.py:440-510` sets `speed_kmh = 0.0` when `frac >= 1.0`. There is no code to advance a train to the next station stop. | Every single train on the corridor sits permanently at Ghaziabad (`lat: 28.6679, lng: 77.4326`) with `0.0 km/h` speed. |
| **3** | **Passenger Tracker Disconnected from Backend Reality** | `passenger_routes.py` never queries ML or live tracker caches; it runs a local client-session elapsed timer with hardcoded 12003 values. | Map movements reset on every browser reload. Different clients see contradictory speeds and positions for the same train. |
| **4** | **Corridor Radar Data Faking** | `demo_routes.py:728` fakes train occupancy whenever `count == 0` instead of dynamically detecting actual trains. | Congestion radar displays synthetic static occupancies regardless of what the live tracker reports. |
| **5** | **Ungraded Prediction Ledger** | 88.8% of prediction ledger receipts remain ungraded because trains never arrive at downstream stations. | Public accountability scoreboard displays a stagnant 27.6% coverage and 18.8 min MAE because only GZB touchdowns ever trigger grading. |

---
*Report compiled autonomously via read-only inspection tools.*  
*Artifact stored at: `audit_probes/BACKEND_STATE.md`.*
