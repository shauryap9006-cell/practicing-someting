"""RailTwin-X FastAPI Routes & Endpoints.

Implements all 10 standard /v1/ endpoints adhering strictly to the frozen scope law.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock
from engine.ops import PlatformManager, CrewDutyEngine, ConnectionCustodyEngine
from engine.simulator import CascadeSimulator
from api.predictor import PredictorService, get_predictor_service
from api.auth import assert_station_scope, get_current_user, require_role
from api.schemas import (
    TrainEtaResponse,
    TrainJourneyResponse,
    JourneyStop,
    ConfidenceBand,
    DelayAutopsyResponse,
    DelayCauseItem,
    NetworkStateResponse,
    NetworkTrainState,
    StationGanttResponse,
    PlatformGanttBlock,
    PlatformGanttConflict,
    ReoptimizeRequest,
    ReoptimizeResponse,
    WhatIfRequest,
    WhatIfResponse,
    CrewAlertsResponse,
    CrewAlertItem,
    ModelsMetaResponse,
    HealthResponse,
    StationSummaryResponse,
)

router = APIRouter(prefix="/v1")
logger = logging.getLogger(__name__)


def _delay_color(delay_min: float) -> str:
    """Maps a delay to the dashboard traffic-light colour using configured thresholds."""
    if delay_min <= settings.DELAY_ON_TIME_MAX_MIN:
        return "green"
    if delay_min <= settings.DELAY_MODERATE_MAX_MIN:
        return "amber"
    return "red"


def _metric(source: Dict[str, Any], key: str, digits: int = 2) -> Optional[float]:
    value = source.get(key)
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


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
        raise HTTPException(status_code=503, detail="Metrics artifact ml/artifacts/metrics.json not found.")

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    h_metrics = metrics.get("metrics_by_horizon", {})
    h1_km = settings.HORIZON_1H_MAX_KM
    h3_km = settings.HORIZON_3H_MAX_KM
    horizon_specs = [
        ("1h", f"1h (<={h1_km:g}km)", f"1 h (<={h1_km:g}km)",
         "Within the first horizon band train physics dominates; ties with the frozen-delay baseline are published honestly."),
        ("3h", f"3h ({h1_km:g}-{h3_km:g}km)", f"3 h ({h1_km:g}-{h3_km:g}km)",
         "Regional horizon captures turnaround buffers, rake deficit, and section headway before stations see it."),
        ("6h", f"6h (>{h3_km:g}km)", f"6 h (>{h3_km:g}km)",
         "Deep corridor foresight: static run-rate baselines degrade while the calibrated cone is preserved."),
    ]

    horizon_cards = []
    for horizon, label, metrics_key, narrative in horizon_specs:
        m = h_metrics.get(metrics_key, {})
        mae = _metric(m, "mae_railtwin")
        b1 = _metric(m, "mae_b1")
        improvement = _metric(m, "improvement_vs_b2_percent", 1)

        # Badge/verdict derived from the measured numbers rather than asserted.
        if mae is not None and b1 is not None and abs(mae - b1) < 0.5:
            badge, verdict = "HONEST TIE", f"{mae - b1:+.2f} min vs frozen delay (physics tie)"
        elif improvement is not None and improvement >= 50.0:
            badge, verdict = "50%+ ADVANTAGE", f"-{improvement:.1f}% vs official run-rate"
        elif improvement is not None and improvement > 0:
            badge, verdict = "OUTPERFORMS", f"-{improvement:.1f}% vs official run-rate"
        else:
            badge, verdict = "UNVERIFIED", "No evaluation data for this horizon"

        horizon_cards.append({
            "horizon": horizon,
            "horizon_label": label,
            "mae": mae,
            "baseline_b1_mae": b1,
            "baseline_b2_mae": _metric(m, "mae_b2"),
            "baseline_b3_mae": _metric(m, "mae_b3"),
            "improvement_vs_official_pct": improvement,
            "coverage_80_pct": _metric(m, "coverage_80_percent", 1),
            "winkler_score": _metric(m, "winkler_score"),
            "verdict": verdict,
            "status_badge": badge,
            "narrative": narrative,
        })

    return {
        "status": "OK",
        "schema_version": metrics.get("schema_version"),
        "canonical_mae": metrics.get("canonical_mae"),
        "overall_mae": _metric(metrics, "overall_mae"),
        "overall_coverage_80": _metric(metrics, "overall_coverage_80"),
        "overall_winkler_score": _metric(metrics, "overall_winkler_score"),
        "overall_crps": _metric(metrics, "overall_crps"),
        "total_test_samples": metrics.get("total_test_samples"),
        "horizon_cards": horizon_cards,
        "proof_table": metrics.get("proof_table", []),
        "metrics_by_horizon": h_metrics,
        "rolling_origin_cv": metrics.get("rolling_origin_cv", {}),
        "audit_note": "All numbers read dynamically from ml/artifacts/metrics.json; badges are derived, not asserted.",
    }


# ----------------------------------------------------
# 1. Trains & Passenger Domain (Extracted to api/routers/trains.py)
# ----------------------------------------------------
from api.routers.trains import (
    router as trains_router,
    get_train_eta,
    get_train_journey,
    get_train_autopsy,
    get_pnr_status,
)

router.include_router(trains_router)



# ----------------------------------------------------
# 4. Network State Corridor View (F1, F10)
# ----------------------------------------------------
@router.get("/network/state", response_model=NetworkStateResponse)
def get_network_state():
    """Returns network-wide active trains, positions, color codes, and platform conflicts."""
    db = get_db()
    clock = get_clock()
    today_str = clock.today_str()

    with db.transaction() as cur:
        cur.execute(
            """
            SELECT train_no, name, class, priority
            FROM trains
            ORDER BY priority ASC, train_no ASC
            """
        )
        train_rows = cur.fetchall()

        cur.execute(
            """
            SELECT train_no, seq, station_code, sched_arr, sched_dep
            FROM route_stations
            ORDER BY train_no, seq
            """
        )
        all_routes = cur.fetchall()

        cur.execute(
            """
            SELECT se.train_no, se.seq, se.station_code, se.delay_arr_min, se.delay_dep_min
            FROM station_events se
            INNER JOIN (
                SELECT train_no, MAX(seq) as max_seq, MAX(run_date) as max_date
                FROM station_events
                GROUP BY train_no
            ) latest ON se.train_no = latest.train_no AND se.seq = latest.max_seq AND se.run_date = latest.max_date
            """
        )
        events_rows = cur.fetchall()

        cur.execute(
            """
            SELECT from_code, to_code, speed_limit_kmph, cause
            FROM speed_restrictions
            WHERE is_active = 1
            """
        )
        tsr_rows = cur.fetchall()

    routes_by_train = {}
    for r in all_routes:
        t = r["train_no"]
        if t not in routes_by_train:
            routes_by_train[t] = []
        routes_by_train[t].append(r)

    events_by_train = {r["train_no"]: r for r in events_rows}

    train_states = []
    delayed_count = 0

    for tr in train_rows:
        t_no = tr["train_no"]
        route = routes_by_train.get(t_no, [])
        ev = events_by_train.get(t_no)

        if route:
            destination = route[-1]["station_code"]
            if ev:
                cur_seq = int(ev["seq"])
                last_stn = ev["station_code"]
                d_min = int(ev["delay_arr_min"] if ev["delay_arr_min"] is not None else (ev["delay_dep_min"] or 0))
                if cur_seq < len(route):
                    next_stn = route[cur_seq]["station_code"]
                else:
                    next_stn = destination
                hops_rem = max(0, len(route) - cur_seq)
            else:
                last_stn = route[0]["station_code"]
                next_stn = route[1]["station_code"] if len(route) > 1 else last_stn
                d_min = 0
                hops_rem = len(route) - 1
        else:
            destination = "DEST"
            last_stn = "ORIG"
            next_stn = "DEST"
            d_min = 0
            hops_rem = 0

        if d_min > settings.DELAY_ON_TIME_MAX_MIN:
            delayed_count += 1

        color = _delay_color(d_min)

        train_states.append(
            NetworkTrainState(
                train_no=t_no,
                train_name=tr["name"],
                train_class=tr["class"],
                priority=int(tr["priority"]),
                last_passed_station=last_stn,
                next_station=next_stn,
                current_delay_min=d_min,
                status_color=color,
                hops_remaining=hops_rem,
                destination=destination,
                predicted_dest_delay_min=d_min,
            )
        )

    # Check active conflicts dynamically
    pm = PlatformManager(db)
    total_conflicts = 0
    with db.transaction() as cur:
        cur.execute("SELECT DISTINCT station_code FROM route_stations")
        active_stns = [r["station_code"] for r in cur.fetchall()]

    for stn_code in active_stns:
        try:
            _, conflicts = pm.get_station_gantt(stn_code)
            total_conflicts += len(conflicts)
        except Exception:
            pass

    active_tsrs = [
        {
            "from_code": r["from_code"],
            "to_code": r["to_code"],
            "speed_limit_kmph": int(r["speed_limit_kmph"]),
            "cause": r["cause"],
        }
        for r in tsr_rows
    ]

    return NetworkStateResponse(
        active_trains_count=len(train_states),
        delayed_trains_count=delayed_count,
        active_conflicts_count=total_conflicts,
        trains=train_states,
        active_tsrs=active_tsrs,
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


@router.get("/stations/{code}", response_model=StationSummaryResponse)
def get_station_summary(code: str):
    """Returns the station contract consumed by the authenticated dashboard shell."""
    station_code = code.strip().upper()
    db = get_db()
    clock = get_clock()
    with db.transaction() as cur:
        cur.execute("SELECT code, name, zone, platforms FROM stations WHERE code = ?", (station_code,))
        station = cur.fetchone()
        if not station:
            raise HTTPException(status_code=404, detail={"code": "STATION_NOT_FOUND", "message": f"Station {station_code} not found", "retryable": False})
        cur.execute("SELECT COUNT(DISTINCT train_no) AS count FROM route_stations WHERE station_code = ?", (station_code,))
        active_trains = int(cur.fetchone()["count"])
        cur.execute(
            "SELECT AVG(COALESCE(delay_arr_min, delay_dep_min, 0)) AS avg_delay FROM station_events WHERE station_code = ?",
            (station_code,),
        )
        avg_delay_row = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) AS count FROM notifications WHERE target_role IN ('station_master', 'dy_sm') AND state IN ('queued', 'sent', 'escalated')",
        )
        advisories_row = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) AS count FROM crew_rosters WHERE station_code = ? AND status = 'BREACH_WARNING'",
            (station_code,),
        )
        crew_row = cur.fetchone()

    conflicts = 0
    try:
        _, conflicts_list = PlatformManager(db).get_station_gantt(station_code)
        conflicts = len(conflicts_list)
    except Exception:
        # A station summary remains useful when optional platform data is absent.
        conflicts = 0

    zone = station["zone"] or "Railway"
    name = station["name"]
    return StationSummaryResponse(
        code=station["code"],
        name=name,
        fullName=f"{name} Junction",
        division=f"{zone} Division",
        zone=zone,
        platformsCount=int(station["platforms"] or 0),
        activeTrainsCount=active_trains,
        platformConflictsCount=conflicts,
        pendingAdvisoriesCount=int(advisories_row["count"] if advisories_row else 0),
        crewWarningsCount=int(crew_row["count"] if crew_row else 0),
        corridorAvgDelayMinutes=round(float(avg_delay_row["avg_delay"] or 0.0), 1) if avg_delay_row else 0.0,
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


# ----------------------------------------------------
# 5. Station Platform Gantt (F8)
# ----------------------------------------------------
@router.get("/stations/{code}/gantt", response_model=StationGanttResponse)
def get_station_gantt(code: str):
    """Returns platform occupancy Gantt blocks and detected conflicts for a station."""
    station_code = code.upper()
    db = get_db()
    clock = get_clock()
    pm = PlatformManager(db)

    with db.transaction() as cur:
        cur.execute("SELECT name, platforms FROM stations WHERE code = ?", (station_code,))
        stn_row = cur.fetchone()
        if not stn_row:
            raise HTTPException(status_code=404, detail={"code": "STATION_NOT_FOUND", "message": f"Station {station_code} not found", "retryable": False})

    blocks, conflicts = pm.get_station_gantt(station_code)

    return StationGanttResponse(
        station_code=station_code,
        station_name=stn_row["name"],
        total_platforms=int(stn_row["platforms"]),
        conflicts_count=len(conflicts),
        blocks=[PlatformGanttBlock(**b.to_dict()) for b in blocks],
        conflicts=[PlatformGanttConflict(**c.to_dict()) for c in conflicts],
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


# ----------------------------------------------------
# 6. Station Platform Re-Optimize (F9)
# ----------------------------------------------------
@router.post("/stations/{code}/reoptimize", response_model=ReoptimizeResponse)
def reoptimize_station_platforms(
    code: str,
    body: Optional[ReoptimizeRequest] = None,
    current_user: dict = Depends(require_role(["station_master", "dy_sm", "admin"])),
):
    """One-click self-healing platform re-optimizer resolving all conflicts in <2s."""
    station_code = code.upper()
    assert_station_scope(current_user, station_code)
    db = get_db()
    clock = get_clock()
    pm = PlatformManager(db)
    target_date = body.target_date if body else None
    blocks, _ = pm.get_station_gantt(station_code, target_date=target_date)
    reopt_blocks, diff = pm.reoptimize_platforms(station_code, blocks)

    return ReoptimizeResponse(
        station_code=station_code,
        conflicts_before=diff.conflicts_before,
        conflicts_after=diff.conflicts_after,
        resolved_conflicts=diff.resolved_conflicts,
        swaps_performed=diff.swaps_performed,
        execution_time_seconds=diff.execution_time_seconds,
        blocks=[PlatformGanttBlock(**b.to_dict()) for b in reopt_blocks],
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


# ----------------------------------------------------
# 7. What-If Cascade Simulation (F6)
# ----------------------------------------------------
@router.post("/simulate/what-if", response_model=WhatIfResponse)
def simulate_what_if(
    req: WhatIfRequest,
    current_user: dict = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
):
    """Simulates injection of operational shock and computes network cascade ripple."""
    db = get_db()
    clock = get_clock()
    assert_station_scope(current_user, req.station_code)
    simulator = CascadeSimulator(db)

    # Convert active TSRs
    tsrs = {}
    if req.active_tsrs:
        for k, v in req.active_tsrs.items():
            if "_" in k:
                u, w = k.split("_", 1)
                tsrs[(u, w)] = float(v)

    run_id, events, total_delays = simulator.run_simulation(
        injected_delays={req.train_no: {req.station_code.upper(): req.injected_delay_min}},
        active_tsrs=tsrs,
        simulation_hours=8.0,
    )

    affected_list = [
        {"train_no": t, "total_delay_min": d, "is_primary_target": (t == req.train_no)}
        for t, d in total_delays.items() if d > 0
    ]

    return WhatIfResponse(
        run_id=run_id,
        scenario={
            "train_no": req.train_no,
            "station": req.station_code.upper(),
            "injected_delay_min": req.injected_delay_min,
        },
        affected_trains_count=len(affected_list),
        affected_trains=affected_list,
        ledger_events=[
            {
                "train_no": ev.train_no,
                "event_type": ev.event_type,
                "minutes": ev.minutes,
                "cause": ev.cause,
                "station_code": ev.station_code,
            }
            for ev in events[:20]
        ],
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


# ----------------------------------------------------
# 8. Crew Duty Breach Alerts (F13)
# ----------------------------------------------------
@router.get("/crew/alerts", response_model=CrewAlertsResponse)
def get_crew_alerts():
    """Returns active crew duty-breach warnings with relief recommendations."""
    db = get_db()
    clock = get_clock()
    engine = CrewDutyEngine(db)
    alerts = engine.evaluate_crew_alerts()

    return CrewAlertsResponse(
        total_alerts=len(alerts),
        alerts=[CrewAlertItem(**a.to_dict()) for a in alerts],
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


# ----------------------------------------------------
# 8b. Connection Custody Engine (Proposal 1)
# ----------------------------------------------------
@router.get("/stations/{code}/connections", response_model=None)
def get_station_connections(
    code: str,
    run_date: Optional[str] = Query(None, description="Date YYYY-MM-DD"),
    min_transfer_min: Optional[int] = Query(
        None, ge=5, le=60, description="Minimum connection transfer time in minutes (defaults to configured value)"
    ),
):
    """Evaluates junction interchange connection feasibility and hold-decision tradeoffs."""
    if min_transfer_min is None:
        min_transfer_min = settings.DEFAULT_MIN_CONNECTION_TIME_MIN
    db = get_db()
    clock = get_clock()
    engine = ConnectionCustodyEngine(db)
    connections = engine.evaluate_station_connections(
        station_code=code,
        run_date=run_date,
        min_connection_time_min=min_transfer_min,
    )

    at_risk_count = sum(1 for c in connections if c.status in ("AT_RISK", "CRITICAL_MISSED", "MISSED"))
    advisories_count = sum(1 for c in connections if c.hold_advisory is not None)

    return {
        "status": "OK",
        "station_code": code.upper(),
        "run_date": run_date or clock.today_str(),
        "total_connections_monitored": len(connections),
        "at_risk_count": at_risk_count,
        "hold_advisories_active": advisories_count,
        "connections": [c.to_dict() for c in connections],
        "as_of": clock.now_iso(),
    }


# ----------------------------------------------------
# 8c. Tamper-Evident Prediction Ledger (Proposal 2)
# ----------------------------------------------------
@router.get("/ledger/scoreboard", response_model=None)
def get_prediction_ledger_scoreboard():
    """Returns unforgeable live calibration scoreboard across served ETA predictions."""
    from engine.prediction_ledger import PredictionLedger
    db = get_db()
    ledger = PredictionLedger(db)
    return {
        "status": "OK",
        "scoreboard": ledger.get_calibration_scoreboard(),
    }


@router.get("/ledger/verify", response_model=None)
def verify_prediction_ledger_chain():
    """Validates cryptographic integrity of entire hash chain from genesis to tip."""
    from engine.prediction_ledger import PredictionLedger
    db = get_db()
    ledger = PredictionLedger(db)
    is_valid, count, broken_id = ledger.verify_chain_integrity()
    return {
        "status": "OK",
        "chain_integrity_verified": is_valid,
        "total_blocks_verified": count,
        "broken_at_block_id": broken_id,
    }


# ----------------------------------------------------
# 9. Model Metadata & Proof Table (F14)
# ----------------------------------------------------
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
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) AS count FROM stations")
        total = int(cur.fetchone()["count"])
        cur.execute(
            "SELECT code, name, is_junction, platforms, lat, lon FROM stations ORDER BY rowid ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cur.fetchall()
    return {"stations": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/meta/trains")
def get_meta_trains(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Returns a bounded page of trains in the database."""
    db = get_db()
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) AS count FROM trains")
        total = int(cur.fetchone()["count"])
        cur.execute(
            "SELECT train_no, name, class, priority FROM trains ORDER BY priority ASC, train_no ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cur.fetchall()
    return {"trains": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/meta/clock")
def get_meta_clock():
    """Returns current simulated / virtual clock metadata (F02, F28)."""
    from engine.sim_clock import get_sim_clock
    return get_sim_clock().get_status()


@router.post("/advise")
def post_brain_advise(
    payload: dict,
    current_user: dict = Depends(require_role(["station_master", "section_controller", "admin"])),
):
    """Executes the full perception -> ML inference -> Safety Interlock -> Conflict Scan pipeline."""
    from api.brain import BrainOrchestrator
    train_no = payload.get("train_no")
    target_station = payload.get("target_station")
    if not train_no:
        raise HTTPException(status_code=400, detail={"code": "MISSING_TRAIN_NO", "message": "train_no is required in request payload", "retryable": False})
    if target_station:
        assert_station_scope(current_user, str(target_station))

    orchestrator = BrainOrchestrator()
    return orchestrator.advise(train_no=str(train_no), target_station_code=target_station)


@router.get("/conflicts/{train_no}")
def get_train_conflicts(train_no: str):
    """Scans deterministic spatial track headway and single-line opposing conflicts for train_no."""
    from engine.conflicts import ConflictScanner
    scanner = ConflictScanner()
    conflicts = scanner.scan_train_conflicts(train_no)
    return {
        "train_no": train_no,
        "conflicts_count": len(conflicts),
        "conflicts": [c.to_dict() for c in conflicts],
        "human_ack_required": True,
    }


# ----------------------------------------------------
# ----------------------------------------------------
# Phase 5: Dispatcher ACK Endpoint & Service Helper
# ----------------------------------------------------
from api.schemas import DispatcherAckRequest, DispatcherAckResponse, WhatsAppWebhookResponse
from notifications.health import get_health_tracker
from notifications.webhook_verify import verify_hmac


def record_advisory_ack(
    adv_id: str,
    decision: str,
    dispatcher_id: Optional[str] = None,
    comment: Optional[str] = None,
    channel: str = "web",
) -> dict:
    """Helper to record human dispatcher / field staff accept or reject decision."""
    clock = get_clock()
    recorded_at = clock.now_iso()
    db = get_db()

    with db.transaction() as cur:
        # Ensure advisory_ack_log table exists
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS advisory_ack_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              adv_id TEXT NOT NULL,
              decision TEXT NOT NULL CHECK(decision IN ('accepted', 'rejected')),
              dispatcher_id TEXT,
              comment TEXT,
              recorded_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            INSERT INTO advisory_ack_log (adv_id, decision, dispatcher_id, comment, recorded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (adv_id, decision, dispatcher_id, comment, recorded_at),
        )
        # Update matching notification_log entry if exists
        try:
            cur.execute(
                """
                UPDATE notification_log
                SET ack_at = ?, status = ?
                WHERE id IN (
                    SELECT id FROM notification_log
                    WHERE payload LIKE ? AND ack_at IS NULL
                    ORDER BY id DESC LIMIT 1
                )
                """,
                (recorded_at, f"acked_{decision}", f"%{adv_id}%"),
            )
        except Exception:
            pass

    return {
        "adv_id": adv_id,
        "decision": decision,
        "dispatcher_id": dispatcher_id,
        "comment": comment,
        "recorded_at": recorded_at,
        "channel": channel,
        "status": "ok",
    }


@router.post("/advise/{adv_id}/ack", response_model=DispatcherAckResponse)
def post_advisory_ack(
    adv_id: str,
    payload: DispatcherAckRequest,
    current_user: dict = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
):
    """Records dispatcher acknowledgement (accept/reject) for an advisory.

    Stores the decision in the advisory_ack_log table for audit trail.
    Used by the frontend dispatcher interface to close the human-in-the-loop loop.
    """
    if payload.decision not in ("accepted", "rejected"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DECISION",
                "message": "decision must be 'accepted' or 'rejected'",
                "retryable": False,
            },
        )

    res = record_advisory_ack(
        adv_id=adv_id,
        decision=payload.decision,
        dispatcher_id=current_user["id"],
        comment=payload.comment,
        channel="web",
    )

    return DispatcherAckResponse(
        adv_id=res["adv_id"],
        decision=res["decision"],
        dispatcher_id=res["dispatcher_id"],
        comment=res["comment"],
        recorded_at=res["recorded_at"],
        status="ok",
    )


# ----------------------------------------------------
# Phase 3: OpenWA Inbound WhatsApp Webhook Endpoint
# ----------------------------------------------------
@router.post("/hooks/whatsapp", response_model=WhatsAppWebhookResponse)
async def whatsapp_inbound_webhook(request: Request):
    """Inbound webhook receiver from OpenWA gateway.

    Handles:
    1. session.status: updates WhatsApp gateway health status.
    2. message.received: parses 'ACK <id>' and 'ESC <id>' to close advisory loops.
    """
    body = await request.body()
    if not verify_hmac(body, request.headers, settings.OPENWA_WEBHOOK_SECRET, require_timestamp=True):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED_WEBHOOK", "message": "Invalid HMAC signature", "retryable": False},
        )

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    event = (
        payload.get("event")
        or payload.get("type")
        or payload.get("event_type")
        or ""
    )

    health = get_health_tracker()

    # 1. Session status event
    if event == "session.status" or "status" in payload:
        status_val = payload.get("status") or payload.get("data", {}).get("status") or "unknown"
        health.set_whatsapp_status(status_val, event_type="session.status")
        return WhatsAppWebhookResponse(ok=True, event="session.status", action="status_updated")

    # 2. Inbound message event (Reply-to-ACK)
    raw_text = (
        payload.get("body")
        or payload.get("text")
        or payload.get("data", {}).get("body")
        or payload.get("data", {}).get("text")
        or ""
    )
    sender_raw = (
        payload.get("from")
        or payload.get("chatId")
        or payload.get("data", {}).get("from")
        or payload.get("data", {}).get("chatId")
        or ""
    )
    sender = sender_raw.split("@")[0].replace("+", "").strip()
    clean_text = raw_text.strip()
    upper_text = clean_text.upper()

    if upper_text.startswith("ACK ") or upper_text.startswith("ACCEPT "):
        adv_id = clean_text.split(" ", 1)[1].strip()
        record_advisory_ack(
            adv_id=adv_id,
            decision="accepted",
            dispatcher_id=sender or "WHATSAPP-USER",
            comment=f"Accepted via WhatsApp ({sender})",
            channel="whatsapp",
        )
        return WhatsAppWebhookResponse(
            ok=True,
            event="message.received",
            action="accepted",
            adv_id=adv_id,
            sender=sender,
        )
    elif upper_text.startswith("ESC ") or upper_text.startswith("REJ ") or upper_text.startswith("REJECT "):
        adv_id = clean_text.split(" ", 1)[1].strip()
        record_advisory_ack(
            adv_id=adv_id,
            decision="rejected",
            dispatcher_id=sender or "WHATSAPP-USER",
            comment=f"Escalated/Rejected via WhatsApp ({sender})",
            channel="whatsapp",
        )
        return WhatsAppWebhookResponse(
            ok=True,
            event="message.received",
            action="rejected",
            adv_id=adv_id,
            sender=sender,
        )

    return WhatsAppWebhookResponse(
        ok=True,
        event=event or "unhandled",
        action="ignored",
        sender=sender,
    )


# ----------------------------------------------------
# 10. Health Check
# ----------------------------------------------------
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

    # Evaluation metrics fold analysis (honest reporting: partial evaluation is transparent, not fatal)
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
                f for f in folds
                if not f.get("error") and isinstance(f.get("samples"), int) and f.get("samples", 0) > 0
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
        test_pred = ps.predict_train_eta(settings.DEMO_DEFAULT_TRAIN_NO, settings.DEFAULT_JUNCTION_CODE)
        if test_pred and ("pred_delay_p50" in test_pred or "predicted_delay_min" in test_pred):
            smoke_test_ready = True
        else:
            smoke_test_error = "smoke test prediction missing expected delay fields"
    except Exception as exc:
        logger.warning("health: inference smoke test failed: %s", exc)
        smoke_test_error = type(exc).__name__

    models_ready = not missing_artifacts and integrity_ready and smoke_test_ready
    model_failures = missing_artifacts + integrity_failures + ([f"smoke_test: {smoke_test_error}"] if not smoke_test_ready else [])
    models_status = "loaded and verified" if models_ready else f"unavailable: {', '.join(model_failures)}"

    migrations_ready = False
    migration_status = "missing"
    try:
        with db.transaction() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM schema_migrations")
            migration_count = int(cur.fetchone()["count"])
        migrations_ready = migration_count > 0
        migration_status = f"applied ({migration_count})"
    except Exception:
        migration_status = "not initialized"

    # Inspect live tracker liveness
    try:
        from engine.live_tracker import get_live_tracker
        from api.sse_limits import active_sse_connections
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

    # Live Drift & Model Trust Telemetry (Wiring Plan 4)
    drift_val = "GREEN"
    trust_val = "HIGH"
    drift_rep_path = settings.ARTIFACTS_DIR / "drift_report.json"
    if drift_rep_path.exists():
        try:
            with open(drift_rep_path, "r", encoding="utf-8") as f:
                d_data = json.load(f)
                drift_val = d_data.get("overall_status", "GREEN")
                trust_val = "HIGH" if drift_val == "GREEN" else "MODERATE" if drift_val == "AMBER" else "DEGRADED"
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
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=response.model_dump())
    return response
