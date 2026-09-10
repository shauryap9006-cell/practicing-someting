"""Train ETA, journey timeline, delay autopsy, and PNR tracking router."""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query


def _add_min_to_sched(s_time: Optional[str], mins: float, base_time: datetime.datetime) -> str:
    if not s_time or ":" not in s_time:
        dt = base_time + datetime.timedelta(minutes=mins)
        return dt.strftime("%H:%M")
    try:
        sh, sm = [int(x) for x in s_time.split(":")[:2]]
        dt = datetime.datetime(
            base_time.year, base_time.month, base_time.day, sh, sm
        ) + datetime.timedelta(minutes=mins)
        return dt.strftime("%H:%M")
    except Exception:
        dt = base_time + datetime.timedelta(minutes=mins)
        return dt.strftime("%H:%M")

from api.predictor import get_predictor_service
from api.schemas import (
    ConfidenceBand,
    DelayAutopsyResponse,
    DelayCauseItem,
    JourneyStop,
    TrainEtaResponse,
    TrainJourneyResponse,
)
from api.services.common import delay_color
from api.services.train_service import (
    get_latest_station_event,
    get_pnr_candidate_trains,
    get_pnr_route_stops,
    get_train_info,
    get_train_route_stops,
)
from data.db import get_db
from engine.attribution import get_attribution_engine
from engine.clocks import get_clock

router = APIRouter()
logger = logging.getLogger(__name__)

# Pre-warm champion predictor and static metadata caches on module import
try:
    _WARMED_PREDICTOR = get_predictor_service()
    if hasattr(_WARMED_PREDICTOR, "snapshot_gen") and _WARMED_PREDICTOR.snapshot_gen:
        _WARMED_PREDICTOR.snapshot_gen._load_metadata_caches()
        _WARMED_PREDICTOR.snapshot_gen.compute_train_period_statistics(get_clock().today_str())
        with get_db().transaction() as _cur:
            _cur.execute(
                "SELECT from_code, to_code, speed_limit_kmph, is_active FROM speed_restrictions WHERE is_active = 1"
            )
            _WARMED_PREDICTOR.snapshot_gen._cached_active_tsrs = [dict(r) for r in _cur.fetchall()]
except Exception as _warm_err:
    logger.debug("Predictor warmup skipped: %s", _warm_err)


@router.get("/trains/{train_no}/eta", response_model=TrainEtaResponse)
def get_train_eta(
    train_no: str,
    station: Optional[str] = Query(None, description="Target station code"),
    target_station: Optional[str] = Query(None, description="Target station code alias"),
):
    """Returns calibrated ETA with best/likely/worst confidence band."""
    target_code = (station or target_station or "").upper().strip()
    if not target_code:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "station"],
                    "msg": "Field required: 'station' or 'target_station'",
                    "type": "value_error.missing",
                }
            ],
        )
    predictor = get_predictor_service()
    try:
        res = predictor.predict_train_eta(train_no=train_no, target_station_code=target_code)
        return res
    except ValueError as err:
        raise HTTPException(
            status_code=404,
            detail={"code": "TRAIN_OR_STATION_NOT_FOUND", "message": str(err), "retryable": False},
        )
    except Exception:
        logger.exception("ETA prediction failed for train=%s station=%s", train_no, target_code)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ETA_PREDICTION_ERROR",
                "message": "ETA prediction failed",
                "retryable": True,
            },
        )


@router.get("/trains/{train_no}/journey", response_model=TrainJourneyResponse)
def get_train_journey(train_no: str):
    """Returns chronological journey timeline with sched vs predicted ETAs across all stops."""
    db = get_db()
    clock = get_clock()

    # Query 1: Route stops + station names + train metadata in a single joined query
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT 
                t.name as train_name,
                t.class as train_class,
                COALESCE(t.priority, 2) as train_priority,
                rs.seq,
                rs.station_code,
                rs.sched_arr,
                rs.sched_dep,
                rs.distance_km,
                s.name as station_name
            FROM route_stations rs
            JOIN trains t ON rs.train_no = t.train_no
            JOIN stations s ON rs.station_code = s.code
            WHERE rs.train_no = ?
            ORDER BY rs.seq ASC
            """,
            (train_no,),
        )
        stops = [dict(r) for r in cur.fetchall()]

    if not stops:
        with db.transaction() as cur:
            cur.execute("SELECT name FROM trains WHERE train_no = ?", (train_no,))
            train_exists = cur.fetchone()
        if not train_exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "TRAIN_NOT_FOUND",
                    "message": f"Train {train_no} not found",
                    "retryable": False,
                },
            )
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ROUTE_NOT_FOUND",
                "message": f"No route found for train {train_no}",
                "retryable": False,
            },
        )

    query_iso = clock.now_iso()
    t_now = clock.now()
    if hasattr(t_now, "tzinfo") and t_now.tzinfo is None:
        t_now = t_now.replace(tzinfo=IST_TIMEZONE)

    # Query 2: All station events for this train in a single batch query
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, event_time, run_date
            FROM station_events
            WHERE train_no = ?
            ORDER BY event_time DESC, seq DESC
            """,
            (train_no,),
        )
        events = [dict(r) for r in cur.fetchall()]

    if not events:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_STATION_EVENTS",
                "message": f"No live or historical station events recorded for train {train_no}",
                "retryable": False,
            },
        )

    # Resolve latest fresh event point-in-time
    fresh_events = []
    for ev in events:
        if ev.get("event_time"):
            try:
                ev_dt = datetime.datetime.fromisoformat(ev["event_time"].replace("Z", "+00:00"))
                if ev_dt.tzinfo is None:
                    ev_dt = ev_dt.replace(tzinfo=IST_TIMEZONE)
                if (t_now - ev_dt).total_seconds() <= 86400.0 and ev["event_time"] <= query_iso:
                    fresh_events.append(ev)
            except Exception:
                pass

    if fresh_events:
        latest_ev = fresh_events[0]
        active_run_date = latest_ev.get("run_date") or clock.today_str()
        events_by_seq = {int(e["seq"]): e for e in fresh_events if e.get("run_date") == active_run_date}
        current_delay = float(
            latest_ev["delay_arr_min"]
            if latest_ev["delay_arr_min"] is not None
            else ((latest_ev["delay_dep_min"] or 0.0) or 0.0)
        )
    else:
        latest_ev = events[0] if events else None
        active_run_date = clock.today_str()
        events_by_seq = {}
        current_delay = 0.0

    current_seq = int(latest_ev["seq"]) if (latest_ev and fresh_events) else 1
    curr_stn = latest_ev["station_code"] if (latest_ev and fresh_events) else stops[0]["station_code"]

    events_by_seq_delays = {
        seq: float(e["delay_arr_min"] if e["delay_arr_min"] is not None else (e["delay_dep_min"] or 0.0))
        for seq, e in events_by_seq.items()
    }

    # Resolve soft train position using pre-fetched telemetry
    predictor = get_predictor_service()
    pos_record = predictor.position_resolver.resolve_train_position(
        train_no=train_no,
        route_stops=stops,
        as_of_time=t_now,
        prefetched_event=latest_ev,
    )

    # Ensure track_graph event cache for active run is initialized to prevent per-stop queries
    if (
        hasattr(predictor, "snapshot_gen")
        and predictor.snapshot_gen
        and hasattr(predictor.snapshot_gen, "track_graph")
    ):
        tg = predictor.snapshot_gen.track_graph
        if not hasattr(tg, "_events_cache"):
            tg._events_cache = {}
        if active_run_date not in tg._events_cache:
            tg._events_cache[active_run_date] = []

    # Compute schedule day offsets along route
    sched_days = {}
    cur_day = 0
    prev_min = -1
    for r in stops:
        s_time = r.get("sched_arr") or r.get("sched_dep")
        if s_time and ":" in s_time:
            try:
                h, m = [int(x) for x in s_time.split(":")[:2]]
                tot_min = h * 60 + m
                if prev_min != -1 and tot_min < prev_min - 120:
                    cur_day += 1
                prev_min = tot_min
            except Exception:
                pass
        sched_days[int(r["seq"])] = cur_day

    recency_latency_min = 0.0
    if latest_ev and latest_ev.get("event_time") and fresh_events:
        try:
            ev_dt = datetime.datetime.fromisoformat(latest_ev["event_time"].replace("Z", "+00:00"))
            if ev_dt.tzinfo is None:
                ev_dt = ev_dt.replace(tzinfo=IST_TIMEZONE)
            recency_latency_min = max(0.0, (t_now - ev_dt).total_seconds() / 60.0)
        except Exception:
            pass

    cached_active_tsrs = (
        getattr(predictor.snapshot_gen, "_cached_active_tsrs", None)
        or [t for t in (getattr(predictor.snapshot_gen, "_cached_tsrs", None) or []) if t.get("is_active", 1)]
    )

    # Pre-computed context to execute in-memory ensemble inference with zero additional queries
    prefetched_ctx = {
        "train_row": {
            "name": stops[0]["train_name"],
            "class": stops[0]["train_class"],
            "priority": int(stops[0].get("train_priority", 2)),
        },
        "route": stops,
        "events_by_seq": events_by_seq_delays,
        "latest_ev": latest_ev,
        "run_date": active_run_date,
        "pos_record": pos_record,
        "sched_days": sched_days,
        "record_ledger": False,
        "recency_latency_min": recency_latency_min,
        "cached_active_tsrs": cached_active_tsrs,
    }

    timeline = []
    for st in stops:
        code = st["station_code"]
        seq = int(st["seq"])

        # Call in-memory loaded ensemble via predict_train_eta with value parity
        pred = predictor.predict_train_eta(
            train_no=train_no,
            target_station_code=code,
            prefetched_ctx=prefetched_ctx,
        )

        d_min = pred["predicted_delay_min"]
        p_arr = pred["predicted_arr"]
        band_info = pred["confidence_band"]
        color = delay_color(d_min)

        timeline.append(
            JourneyStop(
                seq=seq,
                station_code=code,
                station_name=st["station_name"],
                distance_km=float(st["distance_km"]),
                sched_arr=st["sched_arr"],
                predicted_arr=p_arr,
                sched_dep=st["sched_dep"],
                predicted_dep=st["sched_dep"],
                delay_min=d_min,
                status_color=color,
                band=ConfidenceBand(**band_info),
            )
        )

    return TrainJourneyResponse(
        train_no=train_no,
        train_name=stops[0]["train_name"],
        train_class=stops[0]["train_class"],
        current_station=pos_record.station_code,
        current_delay_min=int(round(current_delay)),
        timeline=timeline,
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


@router.get("/trains/{train_no}/autopsy", response_model=DelayAutopsyResponse)
def get_train_autopsy(train_no: str):
    """Returns exact causal delay breakdown where minutes sum exactly to total delay by construction."""
    attribution_engine = get_attribution_engine()
    try:
        res = attribution_engine.decompose_train_delay(train_no)
        return DelayAutopsyResponse(
            train_no=res.train_no,
            train_name=res.train_name,
            total_predicted_delay_min=res.total_delay_min,
            is_exact_accounting=res.is_exact_accounting,
            causes=[
                DelayCauseItem(
                    event_type=c.category,
                    minutes=c.minutes,
                    cause=c.cause,
                    station_code=c.station_code,
                    evidence=c.evidence.to_dict() if c.evidence else None,
                    evidence_pointer=c.evidence_pointer,
                )
                for c in res.causes
            ],
            narrative=res.narrative,
            integrity_status=res.integrity_status,
            integrity_checks=res.integrity_checks,
            as_of_ts=res.as_of_ts,
            updated_at=res.as_of_ts,
            clock_mode=attribution_engine.clock.mode,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=404,
            detail={"code": "TRAIN_NOT_FOUND", "message": str(err), "retryable": False},
        )
    except Exception:
        logger.exception("Delay attribution failed for train=%s", train_no)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ATTRIBUTION_ERROR",
                "message": "Delay attribution failed",
                "retryable": True,
            },
        )


@router.get("/pnr/{pnr_no}")
def get_pnr_status(pnr_no: str):
    """Returns passenger booking details, coach position, and live train kinematics for a 10-digit PNR."""
    clean_pnr = pnr_no.strip().replace("-", "")
    if not clean_pnr.isdigit() or len(clean_pnr) != 10:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_PNR",
                "message": "PNR must be a 10-digit numerical identifier (e.g. 2458910342).",
                "retryable": False,
            },
        )

    db = get_db()
    clock = get_clock()
    pnr_hash = sum(int(c) * (idx + 1) for idx, c in enumerate(clean_pnr))

    candidates = get_pnr_candidate_trains(db)
    if not candidates:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "NO_PASSENGER_SERVICES",
                "message": "No passenger services loaded.",
                "retryable": True,
            },
        )
    train_row = candidates[pnr_hash % len(candidates)]
    selected_train_no = train_row["train_no"]
    train_name = train_row["name"]

    stops = get_pnr_route_stops(db, selected_train_no)

    from_code = stops[0]["station_code"]
    to_code = stops[-1]["station_code"]
    sched_dep = stops[0]["sched_dep"] or stops[0]["sched_arr"]
    sched_arr = stops[-1]["sched_arr"] or stops[-1]["sched_dep"]
    station_names = {s["station_code"]: s["station_name"] for s in stops}

    is_chair_car = "shatabdi" in train_name.lower() or "vande" in train_name.lower()
    coach_code = f"C{(pnr_hash % 6) + 1}" if is_chair_car else f"B{(pnr_hash % 5) + 1}"
    berth_1 = (pnr_hash % 68) + 1
    berth_2 = berth_1 + 1

    berth_type_1 = (
        "Window Seat (WS)"
        if is_chair_car
        else ("Lower Berth (LB)" if berth_1 % 8 in (1, 4) else "Side Lower (SL)")
    )
    berth_type_2 = (
        "Aisle Seat (AS)"
        if is_chair_car
        else ("Middle Berth (MB)" if berth_2 % 8 in (2, 5) else "Upper Berth (UB)")
    )

    rake_coaches = (
        [
            "LOCO",
            "EOG",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "C10",
            "C11",
            "C12",
            "EC1",
            "EC2",
            "EOG",
        ]
        if is_chair_car
        else [
            "LOCO",
            "SLR",
            "GEN",
            "B1",
            "B2",
            "B3",
            "B4",
            "B5",
            "A1",
            "A2",
            "H1",
            "S1",
            "S2",
            "S3",
            "S4",
            "S5",
            "S6",
            "SLR",
        ]
    )

    coach_pos = rake_coaches.index(coach_code) + 1 if coach_code in rake_coaches else 5
    platform_num = (pnr_hash % 5) + 1

    return {
        "data_source": "synthetic_demo",
        "authoritative": False,
        "warning": "Synthetic demonstration data; this build is not connected to a reservation system.",
        "pnr_no": clean_pnr,
        "train_no": selected_train_no,
        "train_name": train_name,
        "date_of_journey": clock.today_str(),
        "from_station": {
            "code": from_code,
            "name": station_names.get(from_code, from_code),
            "sched_dep": sched_dep,
            "platform": platform_num,
        },
        "to_station": {
            "code": to_code,
            "name": station_names.get(to_code, to_code),
            "sched_arr": sched_arr,
            "platform": (platform_num % 4) + 1,
        },
        "travel_class": {
            "code": "CC" if is_chair_car else "3A",
            "name": "AC Chair Car" if is_chair_car else "AC 3 Tier",
        },
        "quota": "GENERAL (GN)",
        "charting_status": "CHART PREPARED",
        "passengers": [
            {
                "passenger_no": 1,
                "booking_status": "CNF",
                "current_status": "CNF",
                "coach": coach_code,
                "berth": berth_1,
                "berth_type": berth_type_1,
            },
            {
                "passenger_no": 2,
                "booking_status": "CNF",
                "current_status": "CNF",
                "coach": coach_code,
                "berth": berth_2,
                "berth_type": berth_type_2,
            },
        ],
        "coach_position": {
            "coach": coach_code,
            "position_from_engine": coach_pos,
            "total_coaches": len(rake_coaches),
            "rake_type": "LHB",
            "all_coaches": rake_coaches,
            "platform_guidance": f"Coach {coach_code} stands approx. {coach_pos * 24}m from engine (near Platform {platform_num} middle foot overbridge/escalator).",
        },
        "fare_paid": 1240.0 if is_chair_car else 1580.0,
        "as_of": clock.now_iso(),
    }
