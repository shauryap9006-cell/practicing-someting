"""RailTwin-X REST API Pydantic Schemas.

Defines standard request and response contracts for all 10 /v1/ API endpoints.
All responses carry updated_at and clock_mode ('live' | 'replay').
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class BaseResponse(BaseModel):
    """Common envelope attributes present in all RailTwin-X API responses."""

    updated_at: str = Field(description="ISO timestamp in IST")
    clock_mode: str = Field(description="'live' or 'replay'")


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ConfidenceBand(BaseModel):
    best_p10_min: float = Field(description="10th percentile optimistic delay")
    likely_p50_min: float = Field(description="50th percentile median delay")
    worst_p90_min: float = Field(description="90th percentile pessimistic delay")
    best_arrival: str
    likely_arrival: str
    worst_arrival: str


class ModelMeta(BaseModel):
    name: str = Field(description="Champion model architecture name")
    sha256: str = Field(description="Pinned model artifact SHA-256")
    version: str = Field(default="v3.0", description="Model training version")


class PositionMeta(BaseModel):
    mode_seq: int = Field(description="Bayesian posterior mode sequence position")
    station_code: str = Field(description="Estimated current station/block code")
    confidence: float = Field(description="Posterior probability confidence score [0.0 - 1.0]")
    basis: str = Field(description="'last_event', 'dead_reckoning', 'human_confirmed', or 'explicit_query'")
    source: str = Field(description="'station_events', 'ad_events', or 'manual'")
    age_seconds: float = Field(description="Seconds elapsed since last confirmed telemetry event")
    posterior_probs: Optional[Dict[Union[int, str], float]] = None


class PredictionDriver(BaseModel):
    feature: str = Field(description="Feature name attributing delay delta")
    contribution_min: float = Field(description="Impact in minutes (positive increases delay, negative decreases)")
    direction: str = Field(description="'increases_delay', 'decreases_delay', or 'neutral'")


class TrainEtaResponse(BaseResponse):
    train_no: str
    train_name: str
    target_station: str
    sched_arr: Optional[str]
    predicted_arr: str
    predicted_delay_min: int
    confidence_band: ConfidenceBand
    tier_used: str = Field(description="'Tier2_LightGBM_CQR', 'Tier2_PyTorch_GRU_Champion', or 'Tier1_HistLookup'")
    model: Optional[ModelMeta] = None
    position: Optional[PositionMeta] = None
    feature_version: str = Field(default="v3.0_25feat", description="Corridor feature store version")
    as_of_ts: str = Field(description="Point-in-time ISO timestamp when features were sampled")
    data_freshness_seconds: float = Field(default=0.0, description="Freshness of underlying event feed")
    drivers: List[PredictionDriver] = Field(default_factory=list, description="Top-3 feature attribution delay drivers")
    model_provenance: Optional[Dict[str, Any]] = None


class JourneyStop(BaseModel):
    seq: int
    station_code: str
    station_name: str
    distance_km: float
    sched_arr: Optional[str]
    predicted_arr: Optional[str]
    sched_dep: Optional[str]
    predicted_dep: Optional[str]
    delay_min: int
    status_color: str = Field(description="'green', 'amber', or 'red'")
    band: ConfidenceBand


class TrainJourneyResponse(BaseResponse):
    train_no: str
    train_name: str
    train_class: str
    current_station: str
    current_delay_min: int
    timeline: List[JourneyStop]


class DelayCauseItem(BaseModel):
    event_type: str
    minutes: int
    cause: str
    station_code: Optional[str] = None


class DelayAutopsyResponse(BaseResponse):
    train_no: str
    train_name: str
    total_predicted_delay_min: int
    is_exact_accounting: bool = True
    causes: List[DelayCauseItem]


class NetworkTrainState(BaseModel):
    train_no: str
    train_name: str
    train_class: str
    priority: int
    last_passed_station: str
    next_station: str
    current_delay_min: int
    status_color: str  # green (<=15m), amber (15-60m), red (>60m)
    hops_remaining: int
    destination: str
    predicted_dest_delay_min: int


class NetworkStateResponse(BaseResponse):
    active_trains_count: int
    delayed_trains_count: int
    active_conflicts_count: int
    trains: List[NetworkTrainState]
    active_tsrs: List[dict]


class PlatformGanttBlock(BaseModel):
    train_no: str
    train_name: str = ""
    train_class: str = "superfast"
    platform: int
    start_time: str
    end_time: str
    dwell_min: int = 15
    is_conflicted: bool = False


class PlatformGanttConflict(BaseModel):
    platform: int
    train_1: str
    train_2: str
    overlap_start: str
    overlap_end: str
    overlap_duration_min: int


class StationGanttResponse(BaseResponse):
    station_code: str
    station_name: str
    total_platforms: int
    conflicts_count: int
    blocks: List[PlatformGanttBlock]
    conflicts: List[PlatformGanttConflict]


class ReoptimizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_date: Optional[str] = None


class ReoptimizeResponse(BaseResponse):
    station_code: str
    conflicts_before: int
    conflicts_after: int
    resolved_conflicts: int
    swaps_performed: List[dict]
    execution_time_seconds: float
    blocks: List[PlatformGanttBlock]


class WhatIfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    train_no: str
    station_code: str
    injected_delay_min: int
    active_tsrs: Optional[Dict[str, float]] = None  # {"FROM_TO": 0.5}


class WhatIfResponse(BaseResponse):
    run_id: str
    scenario: dict
    affected_trains_count: int
    affected_trains: List[dict]
    ledger_events: List[dict]


class CrewAlertItem(BaseModel):
    crew_id: str
    train_no: str
    duty_signon_time: str
    projected_trip_end_time: str
    duty_cap_hours: float
    projected_duty_hours: float
    breach_minutes: int
    recommended_relief_station: str
    is_advisory: bool = True
    message: str


class CrewAlertsResponse(BaseResponse):
    total_alerts: int
    alerts: List[CrewAlertItem]


class ModelsMetaResponse(BaseResponse):
    manifest: dict
    metrics: dict


class HealthResponse(BaseModel):
    status: str
    db: str
    models: str
    whatsapp: str = "connected"
    clock_mode: str
    updated_at: str


# Phase 5: Dispatcher ACK schemas
class DispatcherAckRequest(BaseModel):
    """Dispatcher acknowledgement payload."""
    model_config = ConfigDict(extra="forbid")
    decision: str  # "accepted" | "rejected"
    dispatcher_id: Optional[str] = None
    comment: Optional[str] = None


class DispatcherAckResponse(BaseModel):
    adv_id: str
    decision: str
    dispatcher_id: Optional[str]
    comment: Optional[str]
    recorded_at: str
    status: str = "ok"


class WhatsAppWebhookResponse(BaseModel):
    ok: bool
    event: Optional[str] = None
    action: Optional[str] = None
    adv_id: Optional[str] = None
    sender: Optional[str] = None

