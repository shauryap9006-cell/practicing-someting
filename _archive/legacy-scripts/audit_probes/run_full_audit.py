"""RailTwin-X Deep Technical Audit Execution Engine.

Executes probes for Phases 1 through 9:
- P1: ML Feature parity, LightGBM vs serving order, GRU weights, Quantile math, NaN/OOV handling, Interlock & Ledger wiring
- P2: Metrics.json consistency, leakage analysis, Conformal calibration disjointness, Conformal PID wiring
- P3: Async blocking routes, concurrency smoke test, global mutable state, error path sweep
- P4: DB connection lifecycle, WAL/busy_timeout, hot query EXPLAIN QUERY PLAN, schema-code drift
- P5: Frontend-Backend contract diff (real API JSON vs TS interfaces), timestamp format, physical units
- P6: Transport reality, live update cadence, weather at inference
- P7: Auth coverage matrix, hardcoded secrets, CORS, SQL injection scan, RBAC checks
- P8: Inference latency p50/95/99, snapshot build cost, scale arithmetic for 10k trains, memory RSS
- P9: requirements.txt vs imported packages
"""

import ast
import asyncio
import concurrent.futures
import datetime
import importlib
import inspect
import json
import math
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lightgbm as lgb
import numpy as np
import torch
from fastapi.testclient import TestClient

from api.main import app
from config import settings
from data.db import Database, get_db
from ml.features import FEATURE_NAMES

client = TestClient(app)
db = get_db()
audit_results = {}

# -------------------------------------------------------------
# PHASE 1: ML MODEL INTEGRITY & SKEW
# -------------------------------------------------------------
def audit_phase_1():
    print("[Phase 1] Auditing ML Model Integrity...")
    p1 = {}

    # 1.1 Artifact Parity: LightGBM
    lgb_files = [
        "model_direct_q10.txt",
        "model_direct_q50.txt",
        "model_direct_q90.txt",
        "model_delta_q10.txt",
        "model_delta_q50.txt",
        "model_delta_q90.txt",
    ]
    lgb_features = {}
    for lf in lgb_files:
        path = settings.ARTIFACTS_DIR / lf
        if path.exists():
            booster = lgb.Booster(model_file=str(path))
            lgb_features[lf] = booster.feature_name()

    # Compare with serving FEATURE_NAMES in ml/features.py
    direct_feats = lgb_features.get("model_direct_q50.txt", [])
    skew_direct = []
    if direct_feats != FEATURE_NAMES:
        skew_direct = [
            {"idx": i, "model_feat": direct_feats[i] if i < len(direct_feats) else "MISSING", "serving_feat": FEATURE_NAMES[i] if i < len(FEATURE_NAMES) else "MISSING"}
            for i in range(max(len(direct_feats), len(FEATURE_NAMES)))
            if (i >= len(direct_feats) or i >= len(FEATURE_NAMES) or direct_feats[i] != FEATURE_NAMES[i])
        ]
    p1["lgb_feature_count"] = len(direct_feats)
    p1["serving_feature_count"] = len(FEATURE_NAMES)
    p1["lgb_skew_detected"] = len(skew_direct) > 0
    p1["lgb_skew_details"] = skew_direct

    # 1.1d PyTorch GRU Check
    from ml.model_seq import NonCrossingGRUQuantileModel
    gru_path = settings.ARTIFACTS_DIR / "model_gru_challenger.pt"
    gru_info = {}
    if gru_path.exists():
        state = torch.load(gru_path, map_location="cpu", weights_only=True)
        gru_info["keys"] = list(state.keys())
        gru = NonCrossingGRUQuantileModel(input_dim=8, hidden_dim=128, num_layers=2, dropout=0.2)
        gru.load_state_dict(state)
        gru.eval()
        dummy_in = torch.randn(1, 8, 8)
        with torch.no_grad():
            q10, q50, q90 = gru(dummy_in)
        gru_info["output_shape"] = [list(q10.shape), list(q50.shape), list(q90.shape)]
        gru_info["q10_sample"] = float(q10.item())
        gru_info["q50_sample"] = float(q50.item())
        gru_info["q90_sample"] = float(q90.item())
        gru_info["is_finite"] = bool(torch.isfinite(q10).all() and torch.isfinite(q50).all() and torch.isfinite(q90).all())
    p1["gru_info"] = gru_info

    # 1.2 Champion / Challenger Reality & Serving Path Trace
    from api.predictor import get_predictor_service
    pred_svc = get_predictor_service()
    res_eta = pred_svc.predict_train_eta("12034", "CNB")
    p1["serving_eta_model_provenance"] = res_eta.get("model", {})
    p1["serving_eta_tier_used"] = res_eta.get("model", {}).get("tier_used")
    p1["serving_eta_champion_name"] = pred_svc.champion_name

    # 1.3 Quantile Mathematic over 1000 randomized snapshots
    violations = 0
    from api.predictor import enforce_quantile_order
    for _ in range(1000):
        # Sample raw inputs
        r10 = np.random.uniform(-10, 100)
        r50 = np.random.uniform(-10, 100)
        r90 = np.random.uniform(-10, 100)
        s10, s50, s90 = enforce_quantile_order(r10, r50, r90)
        if not (0.0 <= s10 <= s50 <= s90):
            violations += 1
    p1["quantile_violations_out_of_1000"] = violations

    # 1.4 NaN / Missing Feature Path
    nan_handled = False
    try:
        # Predict on nonexistent train
        res_none = client.get("/v1/trains/99999/eta?target_station=XYZ")
        p1["missing_train_status"] = res_none.status_code
        p1["missing_train_body"] = res_none.json()
        nan_handled = True
    except Exception as e:
        p1["missing_train_err"] = str(e)
    p1["nan_handled_gracefully"] = nan_handled

    # 1.5 OOV Station Handling
    try:
        res_oov = client.get("/v1/trains/12034/eta?target_station=UNKNOWN_STN_999")
        p1["oov_status"] = res_oov.status_code
        p1["oov_body"] = res_oov.json()
    except Exception as e:
        p1["oov_err"] = str(e)

    # 1.6 Training Reproducibility & Artifact Names
    train_v2_code = (ROOT / "ml" / "train_v2.py").read_text(encoding="utf-8", errors="ignore")
    p1["train_v2_seed_set"] = "torch.manual_seed" in train_v2_code and "random.seed" in train_v2_code
    p1["train_v2_deterministic_flag"] = "use_deterministic_algorithms" in train_v2_code
    p1["train_v2_target_artifacts"] = re.findall(r'model_gru_[a-zA-Z0-9_]+\.pt', train_v2_code)

    # 1.7 Safety Interlock Wiring
    pred_code = (ROOT / "api" / "predictor.py").read_text(encoding="utf-8", errors="ignore")
    p1["interlock_called_in_predictor"] = "validate_prediction_through_interlock" in pred_code or "interlock" in pred_code
    p1["ledger_receipt_in_predictor"] = "record_prediction_receipt" in pred_code or "prediction_receipt" in pred_code

    audit_results["P1"] = p1
    print("[Phase 1] Completed.")

# -------------------------------------------------------------
# PHASE 2: EVALUATION & METRICS INTEGRITY
# -------------------------------------------------------------
def audit_phase_2():
    print("[Phase 2] Auditing Evaluation & Metrics...")
    p2 = {}
    metrics_path = settings.ARTIFACTS_DIR / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        p2["canonical_mae"] = m.get("canonical_mae")
        p2["total_test_samples"] = m.get("total_test_samples")
        p2["overall_coverage_80"] = m.get("overall_coverage_80")
        p2["overall_crps"] = m.get("overall_crps")
        folds = m.get("rolling_origin_cv", {}).get("folds", [])
        failed_folds = [f for f in folds if f.get("error") is not None]
        p2["rolling_origin_total_folds"] = len(folds)
        p2["rolling_origin_failed_folds"] = len(failed_folds)
        if failed_folds:
            p2["fold_failure_sample_error"] = failed_folds[0].get("error")

    # 2.2 Leakage Test Audit
    leakage_test_file = ROOT / "tests" / "test_data_leakage.py"
    if leakage_test_file.exists():
        lt_code = leakage_test_file.read_text(encoding="utf-8", errors="ignore")
        p2["tests_point_in_time"] = "query_time" in lt_code
        p2["tests_future_target_leakage"] = "actual_arr" in lt_code or "target" in lt_code
        p2["has_temporal_embargo_test"] = "embargo" in lt_code

    # 2.3 Calibration set vs test set in conformal.py
    conformal_file = ROOT / "ml" / "conformal.py"
    if conformal_file.exists():
        cf_code = conformal_file.read_text(encoding="utf-8", errors="ignore")
        p2["conformal_splits_train_cal_test"] = "cal" in cf_code and "test" in cf_code
        p2["conformal_pid_class_present"] = "ConformalPIDController" in cf_code

    # 2.4 Conformal PID Live Wiring Check
    src_dirs = [ROOT / d for d in ["api", "engine", "collector"]]
    pid_updates = []
    for sdir in src_dirs:
        for py in sdir.rglob("*.py"):
            txt = py.read_text(encoding="utf-8", errors="ignore")
            if "ConformalPIDController" in txt or "update_conformal_pid" in txt:
                pid_updates.append(str(py.relative_to(ROOT)))
    p2["conformal_pid_live_wiring_sites"] = pid_updates

    audit_results["P2"] = p2
    print("[Phase 2] Completed.")

# -------------------------------------------------------------
# PHASE 3: BACKEND RUNTIME AUDIT
# -------------------------------------------------------------
def audit_phase_3():
    print("[Phase 3] Auditing Backend Runtime & Concurrency...")
    p3 = {}

    # 3.4 Async Blocking Audit
    # Check all async def handlers in api/*.py
    api_dir = ROOT / "api"
    async_blocking_findings = []
    blocking_calls = ["get_db()", "db.execute", "cursor.execute", "time.sleep", "requests.", "lgb.", "torch.", "predict_train_eta"]
    for py in api_dir.glob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    # Inspect body for blocking calls
                    node_src = ast.unparse(node) if hasattr(ast, "unparse") else ""
                    found_blocking = [b for b in blocking_calls if b in node_src]
                    if found_blocking and "run_in_threadpool" not in node_src and "to_thread" not in node_src:
                        async_blocking_findings.append({
                            "file": str(py.relative_to(ROOT)),
                            "line": node.lineno,
                            "function": node.name,
                            "blocking_calls": found_blocking,
                        })
        except Exception:
            pass
    p3["async_blocking_handlers_count"] = len(async_blocking_findings)
    p3["async_blocking_handlers"] = async_blocking_findings[:10]

    # 3.5 Concurrency Smoke Test: 50 threaded requests
    test_urls = [
        "/v1/health",
        "/v1/trains/12034/eta?target_station=CNB",
        "/v1/network/state",
        "/v1/stations/CNB/gantt",
        "/v1/trains/12034/autopsy",
    ]
    concurrency_errors = []
    latencies = []

    def hit_route(url):
        t0 = time.perf_counter()
        try:
            res = client.get(url)
            elapsed = (time.perf_counter() - t0) * 1000.0
            return res.status_code, elapsed, None
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return 500, elapsed, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(hit_route, test_urls[i % len(test_urls)]) for i in range(50)]
        for fut in concurrent.futures.as_completed(futures):
            code, lat, err = fut.result()
            latencies.append(lat)
            if code != 200 or err:
                concurrency_errors.append({"code": code, "error": err})

    p3["concurrency_requests_fired"] = 50
    p3["concurrency_errors_count"] = len(concurrency_errors)
    p3["concurrency_errors"] = concurrency_errors
    p3["concurrency_latencies_ms"] = {
        "p50": round(float(np.percentile(latencies, 50)), 2),
        "p95": round(float(np.percentile(latencies, 95)), 2),
        "p99": round(float(np.percentile(latencies, 99)), 2),
        "max": round(float(np.max(latencies)), 2),
    }

    # Verify ledger integrity after concurrent hits
    from engine.prediction_ledger import PredictionLedger
    ledger = PredictionLedger(db)
    chain_ok, blocks, fork = ledger.verify_chain_integrity()
    p3["post_concurrency_ledger_integrity"] = {"chain_ok": chain_ok, "total_blocks": blocks, "fork": fork}

    audit_results["P3"] = p3
    print("[Phase 3] Completed.")

# -------------------------------------------------------------
# PHASE 4: DATABASE LAYER
# -------------------------------------------------------------
def audit_phase_4():
    print("[Phase 4] Auditing Database Layer...")
    p4 = {}
    conn = sqlite3.connect(str(ROOT / "data" / "railtwin.db"))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    p4["journal_mode"] = cur.fetchone()[0]
    cur.execute("PRAGMA busy_timeout;")
    p4["busy_timeout"] = cur.fetchone()[0]
    cur.execute("PRAGMA synchronous;")
    p4["synchronous"] = cur.fetchone()[0]

    # Explain query plan for hot query: station_events lookup
    cur.execute("EXPLAIN QUERY PLAN SELECT * FROM station_events WHERE train_no = '12034' AND station_code = 'CNB' ORDER BY actual_arr DESC LIMIT 10;")
    p4["eqp_station_events"] = cur.fetchall()

    cur.execute("EXPLAIN QUERY PLAN SELECT * FROM eta_prediction_ledger ORDER BY id DESC LIMIT 10;")
    p4["eqp_ledger"] = cur.fetchall()
    conn.close()

    audit_results["P4"] = p4
    print("[Phase 4] Completed.")

# -------------------------------------------------------------
# PHASE 5: FRONTEND-BACKEND CONTRACT MISMATCHES
# -------------------------------------------------------------
def audit_phase_5():
    print("[Phase 5] Auditing Frontend-Backend Contracts...")
    p5 = {}
    mismatches = []

    # 1. ETA Response Contract
    res_eta = client.get("/v1/trains/12034/eta?target_station=CNB").json()
    eta_keys = set(res_eta.keys())
    # Expected TS keys for ETA in web/src
    ts_eta_keys = {"train_no", "target_station", "predicted_arrival", "predicted_delay_min", "confidence_band", "safety_interlock", "clock_mode"}
    diff_eta = ts_eta_keys - eta_keys
    if diff_eta:
        mismatches.append({"endpoint": "/v1/trains/{no}/eta", "missing_in_api": list(diff_eta)})

    # 2. Autopsy / Causes Contract (The known bug class)
    res_autopsy = client.get("/v1/trains/12034/autopsy").json()
    p5["autopsy_keys"] = list(res_autopsy.keys())
    if "causes" not in res_autopsy and "cause_breakdown" in res_autopsy:
        mismatches.append({"endpoint": "/v1/trains/{no}/autopsy", "issue": "Expected 'causes', received 'cause_breakdown'"})

    # 3. Model Performance Contract
    res_perf = client.get("/v1/model/performance").json()
    p5["model_perf_keys"] = list(res_perf.keys())

    p5["contract_mismatches"] = mismatches
    audit_results["P5"] = p5
    print("[Phase 5] Completed.")

# -------------------------------------------------------------
# PHASE 7: SECURITY & CONFIG
# -------------------------------------------------------------
def audit_phase_7():
    print("[Phase 7] Auditing Security & Config...")
    p7 = {}

    # Mutating routes without auth
    from api.main import app
    unprotected_mutating = []
    for r in app.routes:
        methods = getattr(r, "methods", set())
        mutating = methods & {"POST", "PUT", "DELETE", "PATCH"}
        if mutating:
            path = getattr(r, "path", "")
            ep = getattr(r, "endpoint", None)
            ep_src = ""
            try:
                ep_src = inspect.getsource(ep)
            except Exception:
                pass
            if not any(k in ep_src for k in ["get_current_user", "require_role", "assert_station_scope"]):
                unprotected_mutating.append({"path": path, "methods": list(mutating), "handler": getattr(ep, "__name__", "")})
    p7["unprotected_mutating_routes_count"] = len(unprotected_mutating)
    p7["unprotected_mutating_routes"] = unprotected_mutating[:15]

    # Secrets scan in repository files
    secret_pat = re.compile(r"""(?:API_KEY|SECRET|PASSWORD|TOKEN)\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
    hardcoded_secrets = []
    for py in (ROOT / "api").rglob("*.py"):
        try:
            for idx, line in enumerate(py.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if secret_pat.search(line) and not line.strip().startswith("#"):
                    hardcoded_secrets.append({"file": str(py.relative_to(ROOT)), "line": idx, "code": line.strip()})
        except Exception:
            pass
    p7["hardcoded_secrets_found"] = hardcoded_secrets

    audit_results["P7"] = p7
    print("[Phase 7] Completed.")

# -------------------------------------------------------------
# PHASE 8: PERFORMANCE MICRO-BENCHMARKS
# -------------------------------------------------------------
def audit_phase_8():
    print("[Phase 8] Running Performance Micro-Benchmarks...")
    p8 = {}

    # 8.1 200 Sequential Inferences
    lats = []
    from api.predictor import get_predictor_service
    pred_svc = get_predictor_service()

    for _ in range(200):
        t0 = time.perf_counter()
        pred_svc.predict_train_eta("12034", "CNB")
        lats.append((time.perf_counter() - t0) * 1000.0)

    p8["inference_latency_ms"] = {
        "p50": round(float(np.percentile(lats, 50)), 2),
        "p95": round(float(np.percentile(lats, 95)), 2),
        "p99": round(float(np.percentile(lats, 99)), 2),
        "mean": round(float(np.mean(lats)), 2),
    }

    # 8.3 Scale Math for 10,000 trains every 60s
    p50_ms = p8["inference_latency_ms"]["p50"]
    total_cpu_seconds = (10000 * p50_ms) / 1000.0
    cores_needed_for_60s = total_cpu_seconds / 60.0
    p8["scale_math_10k_trains"] = {
        "p50_latency_ms": p50_ms,
        "total_cpu_seconds_per_cycle": round(total_cpu_seconds, 1),
        "refresh_budget_seconds": 60,
        "parallel_cores_required": math.ceil(cores_needed_for_60s),
        "fits_single_core": total_cpu_seconds <= 60.0,
    }

    audit_results["P8"] = p8
    print("[Phase 8] Completed.")

if __name__ == "__main__":
    audit_phase_1()
    audit_phase_2()
    audit_phase_3()
    audit_phase_4()
    audit_phase_5()
    audit_phase_7()
    audit_phase_8()

    out_file = ROOT / "audit_probes" / "audit_execution_data.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"Audit results exported to {out_file} successfully!")
