"""RailTwin-X Core API Router Facade.

Aggregates domain-specific routers adhering strictly to the frozen scope law:
- trains: /v1/trains/*, /v1/pnr/*
- stations: /v1/stations/*
- ops: /v1/network/state, /v1/simulate/what-if, /v1/crew/alerts
- advisory: /v1/advise, /v1/conflicts/*, /v1/hooks/whatsapp
- system_meta: /v1/evaluation/*, /v1/model/performance, /v1/ledger/*, /v1/meta/*, /v1/health
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routers.trains import (
    router as trains_router,
    get_train_eta,
    get_train_journey,
    get_train_autopsy,
    get_pnr_status,
)
from api.routers.stations import (
    router as stations_router,
    get_station_summary,
    get_station_gantt,
    reoptimize_station_platforms,
    get_station_connections,
)
from api.routers.ops import (
    router as ops_router,
    get_network_state,
    simulate_what_if,
    get_crew_alerts,
)
from api.routers.advisory import (
    router as advisory_router,
    post_brain_advise,
    get_train_conflicts,
    post_advisory_ack,
    whatsapp_inbound_webhook,
)
from api.routers.system_meta import (
    router as system_meta_router,
    get_evaluation_summary,
    get_model_performance,
    get_prediction_ledger_scoreboard,
    verify_prediction_ledger_chain,
    get_models_meta,
    get_meta_stations,
    get_meta_trains,
    get_meta_clock,
    get_health,
)
from api.services.advisory_service import record_advisory_ack

# Root router for v1 endpoints
router = APIRouter(prefix="/v1")

# Mount domain routers
router.include_router(trains_router)
router.include_router(stations_router)
router.include_router(ops_router)
router.include_router(advisory_router)
router.include_router(system_meta_router)

__all__ = [
    "router",
    "get_health",
    "get_train_eta",
    "get_train_journey",
    "get_train_autopsy",
    "get_pnr_status",
    "get_station_summary",
    "get_station_gantt",
    "reoptimize_station_platforms",
    "get_station_connections",
    "get_network_state",
    "simulate_what_if",
    "get_crew_alerts",
    "post_brain_advise",
    "get_train_conflicts",
    "post_advisory_ack",
    "whatsapp_inbound_webhook",
    "record_advisory_ack",
    "get_evaluation_summary",
    "get_model_performance",
    "get_prediction_ledger_scoreboard",
    "verify_prediction_ledger_chain",
    "get_models_meta",
    "get_meta_stations",
    "get_meta_trains",
    "get_meta_clock",
]
