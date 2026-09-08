"""System evaluation, model benchmarks, prediction ledger, catalog metadata, and health router."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.schemas import HealthResponse, ModelsMetaResponse
from api.services.common import format_metric
from api.services.meta_service import (
    get_paginated_stations,
    get_paginated_trains,
    get_schema_migration_count,
)
from config import settings
from data.db import get_db
from engine.clocks import get_clock
from engine.prediction_ledger import PredictionLedger
from engine.sim_clock import get_sim_clock
from notifications.health import get_health_tracker

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/evaluation/summary")
def get_evaluation_summary():
    """Returns empirical backtest proof table metrics evaluated on held-out test week."""
    metrics_path = settings.ARTIFACTS_DIR / "metrics.json"
    if metrics_path.exists():
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "status": "NO_EVALUATION_YET",
        "message": "No evaluation data yet — run evaluate.py",
        "proof_table": [],
        "metrics_by_horizon": {},
        "overall_mae": None,
        "overall_coverage_80": None,
    }


@router.get("/model/performance")
def get_model_performance():
    """Returns canonical model performance benchmarks, proof tables, and honest horizon cards from metrics.json."""
    metrics_path = settings.ARTIFACTS_DIR / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=503, detail="Metrics artifact ml/artifacts/metrics.json not found."
        )

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    h_metrics = metrics.get("metrics_by_horizon", {})
    h1_km = settings.HORIZON_1H_MAX_KM
    h3_km = settings.HORIZON_3H_MAX_KM
    horizon_specs = [
        (
            "1h",
            f"1h (<={h1_km:g}km)",
            f"1 h (<={h1_km:g}km)",
            "Within the first horizon band train physics dominates; ties with the frozen-delay baseline are published honestly.",
        ),
        (
            "3h",
            f"3h ({h1_km:g}-{h3_km:g}km)",
            f"3 h ({h1_km:g}-{h3_km:g}km)",
            "Regional horizon captures turnaround buffers, rake deficit, and section headway before stations see it.",
        ),
        (
            "6h",
            f"6h (>{h3_km:g}km)",
            f"6 h (>{h3_km:g}km)",
            "Deep corridor foresight: static run-rate baselines degrade while the calibrated cone is preserved.",
        ),
    ]

    horizon_cards = []
    for horizon, label, metrics_key, narrative in horizon_specs:
        m = h_metrics.get(metrics_key, {})
        mae = format_metric(m, "mae_railtwin")
        b1 = format_metric(m, "mae_b1")
        improvement = format_metric(m, "improvement_vs_b2_percent", 1)

        # Badge/verdict derived from the measured numbers rather than asserted.
        if mae is not None and b1 is not None and abs(mae - b1) < 0.5:
            badge, verdict = "HONEST TIE", f"{mae - b1:+.2f} min vs frozen delay (physics tie)"
        elif improvement is not None and improvement >= 50.0:
            badge, verdict = "50%+ ADVANTAGE", f"-{improvement:.1f}% vs official run-rate"
        elif improvement is not None and improvement > 0:
            badge, verdict = "OUTPERFORMS", f"-{improvement:.1f}% vs official run-rate"
        else:
            badge, verdict = "UNVERIFIED", "No evaluation data for this horizon"

        horizon_cards.append(
            {
                "horizon": horizon,
                "horizon_label": label,
                "mae": mae,
                "baseline_b1_mae": b1,
                "baseline_b2_mae": format_metric(m, "mae_b2"),
                "baseline_b3_mae": format_metric(m, "mae_b3"),
                "improvement_vs_official_pct": improvement,
                "coverage_80_pct": format_metric(m, "coverage_80_percent", 1),
                "winkler_score": format_metric(m, "winkler_score"),
                "verdict": verdict,
                "status_badge": badge,
                "narrative": narrative,
            }
        )

    return {
        "status": "OK",
        "schema_version": metrics.get("schema_version"),
        "canonical_mae": metrics.get("canonical_mae"),
        "overall_mae": format_metric(metrics, "overall_mae"),
        "overall_coverage_80": format_metric(metrics, "overall_coverage_80"),
        "overall_winkler_score": format_metric(metrics, "overall_winkler_score"),
        "overall_crps": format_metric(metrics, "overall_crps"),
        "total_test_samples": metrics.get("total_test_samples"),
        "horizon_cards": horizon_cards,
        "proof_table": metrics.get("proof_table", []),
        "metrics_by_horizon": h_metrics,
        "rolling_origin_cv": metrics.get("rolling_origin_cv", {}),
        "audit_note": "All numbers read dynamically from ml/artifacts/metrics.json; badges are derived, not asserted.",
    }


@router.get("/ledger/scoreboard", response_model=None)
def get_prediction_ledger_scoreboard():
    """Returns unforgeable live calibration scoreboard across served ETA predictions."""
    db = get_db()
    ledger = PredictionLedger(db)
    return {
        "status": "OK",
        "scoreboard": ledger.get_calibration_scoreboard(),
    }


@router.get("/ledger/verify", response_model=None)
def verify_prediction_ledger_chain():
    """Validates cryptographic integrity of entire hash chain from genesis to tip."""
    db = get_db()
    ledger = PredictionLedger(db)
    is_valid, count, broken_id = ledger.verify_chain_integrity()
    return {
        "status": "OK",
        "chain_integrity_verified": is_valid,
        "total_blocks_verified": count,
        "broken_at_block_id": broken_id,
    }


@router.get("/meta/models", response_model=ModelsMetaResponse)
def get_models_meta():
    """Returns model versions, 17 features, training window, and F14 proof table."""
    clock = get_clock()
    manifest_file = settings.ARTIFACTS_DIR / "manifest.json"
    metrics_file = settings.ARTIFACTS_DIR / "metrics.json"

    manifest = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    metrics = {}
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

    return ModelsMetaResponse(
        manifest=manifest,
        metrics=metrics,
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


@router.get("/meta/stations")
def get_meta_stations(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Returns a bounded page of stations in the database."""
    db = get_db()
    rows, total = get_paginated_stations(db, limit=limit, offset=offset)
    return {"stations": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/meta/trains")
def get_meta_trains(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Returns a bounded page of trains in the database."""
    db = get_db()
    rows, total = get_paginated_trains(db, limit=limit, offset=offset)
    return {"trains": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/meta/clock")
def get_meta_clock():
    """Returns current simulated / virtual clock metadata (F02, F28)."""
    return get_sim_clock().get_status()


@router.get("/health", response_model=HealthResponse)
def get_health():
    """System liveness and component readiness check."""
    clock = get_clock()
    db = get_db()
    health = get_health_tracker()

    db_ready = True
    try:
        counts = db.table_counts()
        db_status = f"connected ({counts.get('station_events', 0):,} events)"
        live_pos_count = counts.get("live_positions", 0)
    except Exception:
        logger.exception("health: database check failed")
        db_ready = False
        db_status = "error"
        live_pos_count = 0

    required_artifacts = [
        settings.ARTIFACTS_DIR / "manifest.json",
        settings.ARTIFACTS_DIR / "model_direct_q10.txt",
        settings.ARTIFACTS_DIR / "model_direct_q50.txt",
        settings.ARTIFACTS_DIR / "model_direct_q90.txt",
        settings.ARTIFACTS_DIR / "artifact_integrity.json",
        settings.ARTIFACTS_DIR / "metrics.json",
    ]
    missing_artifacts = [path.name for path in required_artifacts if not path.is_file()]
    from ml.artifact_integrity import verify_artifacts

    integrity_ready, integrity_failures = verify_artifacts(settings.ARTIFACTS_DIR)

    # Evaluation metrics fold analysis
    metrics_ready = False
    metrics_failures: list[str] = []
    evaluation_status = "unverified"
    valid_folds_count = 0
    total_folds_count = 0
    metrics_path = settings.ARTIFACTS_DIR / "metrics.json"
    if metrics_path.is_file():
        try:
            with metrics_path.open("r", encoding="utf-8") as stream:
                metrics = json.load(stream)
            folds = metrics.get("rolling_origin_cv", {}).get("folds", [])
            total_folds_count = len(folds)
            valid_folds = [
                f
                for f in folds
                if not f.get("error")
                and isinstance(f.get("samples"), int)
                and f.get("samples", 0) > 0
            ]
            valid_folds_count = len(valid_folds)
            if total_folds_count > 0:
                if valid_folds_count == total_folds_count:
                    evaluation_status = "complete"
                elif valid_folds_count > 0:
                    evaluation_status = "partial"
                else:
                    evaluation_status = "failed"
            metrics_ready = valid_folds_count > 0
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            metrics_failures.append(f"invalid metrics.json: {exc}")

    # Real inference smoke test through PredictorService
    smoke_test_ready = False
    smoke_test_error: Optional[str] = None
    try:
        from api.predictor import get_predictor_service

        ps = get_predictor_service()
        test_pred = ps.predict_train_eta(
            settings.DEMO_DEFAULT_TRAIN_NO, settings.DEFAULT_JUNCTION_CODE
        )
        if test_pred and ("pred_delay_p50" in test_pred or "predicted_delay_min" in test_pred):
            smoke_test_ready = True
        else:
            smoke_test_error = "smoke test prediction missing expected delay fields"
    except Exception as exc:
        logger.warning("health: inference smoke test failed: %s", exc)
        smoke_test_error = type(exc).__name__

    models_ready = not missing_artifacts and integrity_ready and smoke_test_ready
    model_failures = (
        missing_artifacts
        + integrity_failures
        + ([f"smoke_test: {smoke_test_error}"] if not smoke_test_ready else [])
    )
    models_status = (
        "loaded and verified" if models_ready else f"unavailable: {', '.join(model_failures)}"
    )

    migrations_ready = False
    migration_status = "missing"
    try:
        migration_count = get_schema_migration_count(db)
        migrations_ready = migration_count > 0
        migration_status = f"applied ({migration_count})"
    except Exception:
        migration_status = "not initialized"

    # Inspect live tracker liveness
    try:
        from api.sse_limits import active_sse_connections
        from engine.live_tracker import get_live_tracker

        tracker = get_live_tracker(db)
        last_tick = tracker.last_tick_time
        if last_tick:
            age_sec = max(0.0, (clock.now() - last_tick).total_seconds())
        else:
            age_sec = 0.0
        active_sse = active_sse_connections()
    except Exception:
        age_sec = None
        active_sse = 0

    # Live Drift & Model Trust Telemetry
    drift_val = "GREEN"
    trust_val = "HIGH"
    drift_rep_path = settings.ARTIFACTS_DIR / "drift_report.json"
    if drift_rep_path.exists():
        try:
            with open(drift_rep_path, "r", encoding="utf-8") as f:
                d_data = json.load(f)
                drift_val = d_data.get("overall_status", "GREEN")
                trust_val = (
                    "HIGH"
                    if drift_val == "GREEN"
                    else "MODERATE"
                    if drift_val == "AMBER"
                    else "DEGRADED"
                )
        except Exception:
            pass

    ready = db_ready and models_ready and migrations_ready
    response = HealthResponse(
        status="healthy" if ready else "not_ready",
        ready=ready,
        db=db_status,
        models=models_status,
        migrations=migration_status,
        components={
            "database": db_ready,
            "models": models_ready,
            "model_artifacts_integrity": integrity_ready,
            "inference_smoke_test": smoke_test_ready,
            "evaluation": {
                "status": evaluation_status,
                "valid_folds": valid_folds_count,
                "total_folds": total_folds_count,
            },
            "evaluation_metrics": metrics_ready,
            "migrations": migrations_ready,
        },
        whatsapp=health.whatsapp_status,
        clock_mode=clock.mode,
        updated_at=clock.now_iso(),
        live_tracker_last_tick_age_seconds=round(age_sec, 1) if age_sec is not None else None,
        active_sse_clients=active_sse,
        adapter_tier_in_use="replay_synthetic" if clock.mode == "replay" else "live_provider_chain",
        live_positions_count=live_pos_count,
        drift_status=drift_val,
        model_trust=trust_val,
    )
    if not ready:
        return JSONResponse(status_code=503, content=response.model_dump())
    return response
