"""Network corridor state, cascade what-if simulation, and crew alerts router."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException

from api.auth import assert_station_scope, require_role
from api.schemas import (
    CrewAlertItem,
    CrewAlertsResponse,
    NetworkStateResponse,
    NetworkTrainState,
    WhatIfRequest,
    WhatIfResponse,
)
from api.services.common import delay_color
from api.services.ops_service import (
    get_active_route_station_codes,
    get_network_state_raw,
)
from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock
from engine.ops import CrewDutyEngine, PlatformManager
from engine.simulator import CascadeSimulator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/network/state", response_model=NetworkStateResponse)
def get_network_state():
    """Returns network-wide active trains, positions, color codes, and platform conflicts."""
    db = get_db()
    clock = get_clock()

    raw = get_network_state_raw(db)
    train_rows = raw["trains"]
    all_routes = raw["routes"]
    events_rows = raw["events"]
    tsr_rows = raw["tsrs"]

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

        color = delay_color(d_min)

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
    active_stns = get_active_route_station_codes(db)

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
