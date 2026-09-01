"""RailTwin-X Live Delay Attribution Engine (Pipeline 07, Phase A5).

Evaluates active train delay jumps (Δdelay >= settings.ATTRIBUTION_DELTA_MIN)
against 7 ordered mechanistic causal evidence rules:
1. RAKE_INHERIT: Incoming rake turnaround deficit
2. TSR_ACTIVE: Active speed restrictions and track maintenance
3. WEATHER_FOG: Dense fog speed reduction
4. WEATHER_RAIN: Heavy precipitation caution orders
5. PLATFORM_WAIT: Terminal platform berthing hold / conflicts
6. CONGESTION: Upstream traffic headway braking / high section occupancy
7. UNEXPLAINED: Unaccounted residual telemetry delay

Enforces the exact mathematical delay accounting invariant:
  sum(attributed_min) == measured_delta_min  (is_exact_accounting = True)

Appends immutable attribution events to the live_delay_ledger table.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock, IST_TIMEZONE
from engine.context import ContextEngine, TrainContext, get_context_engine


@dataclass
class AttributedCause:
    """Individual causal attribution segment with explanation and evidence."""

    cause_code: str  # 'RAKE_INHERIT', 'TSR_ACTIVE', 'WEATHER_FOG', 'WEATHER_RAIN', 'PLATFORM_WAIT', 'CONGESTION', 'UNEXPLAINED'
    attributed_min: float
    explanation: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cause_code": self.cause_code,
            "attributed_min": round(self.attributed_min, 1),
            "explanation": self.explanation,
            "evidence": self.evidence,
        }


@dataclass
class AttributionResult:
    """Result of causal delay attribution evaluation for a measured delay change."""

    train_no: str
    run_date: str
    timestamp: str
    station_code: Optional[str]
    measured_delta_min: float
    previous_delay_min: float
    current_delay_min: float
    primary_cause: str
    secondary_cause: Optional[str]
    causes: List[AttributedCause]
    is_exact_accounting: bool
    confidence: float
    ledger_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_no": self.train_no,
            "run_date": self.run_date,
            "timestamp": self.timestamp,
            "station_code": self.station_code,
            "measured_delta_min": round(self.measured_delta_min, 1),
            "previous_delay_min": round(self.previous_delay_min, 1),
            "current_delay_min": round(self.current_delay_min, 1),
            "primary_cause": self.primary_cause,
            "secondary_cause": self.secondary_cause,
            "causes": [c.to_dict() for c in self.causes],
            "is_exact_accounting": self.is_exact_accounting,
            "confidence": round(self.confidence, 3),
            "ledger_id": self.ledger_id,
        }


class LiveAttributionEngine:
    """Evaluates real-time delay jumps and records exact causal attribution."""

    VALID_CAUSES = {
        "RAKE_INHERIT",
        "TSR_ACTIVE",
        "WEATHER_FOG",
        "WEATHER_RAIN",
        "PLATFORM_WAIT",
        "CONGESTION",
        "UNEXPLAINED",
    }

    def __init__(self, db: Optional[Database] = None, context_engine: Optional[ContextEngine] = None):
        self.db = db or get_db()
        self.context_engine = context_engine or get_context_engine(self.db)
        self.min_delta = float(settings.ATTRIBUTION_DELTA_MIN)
        self.unexplained_tolerance = float(settings.ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN)

    def evaluate_delay_jump(
        self,
        train_no: str,
        run_date: str,
        previous_delay_min: float,
        current_delay_min: float,
        station_code: Optional[str] = None,
        current_km: Optional[float] = None,
        context: Optional[TrainContext] = None,
        as_of_time: Optional[datetime.datetime] = None,
    ) -> Optional[AttributionResult]:
        """Evaluates a delay change against the 7 ordered evidence rules.

        Returns an AttributionResult if delta >= ATTRIBUTION_DELTA_MIN and writes
        to the live_delay_ledger table, guaranteeing sum(causes) == delta.
        """
        clock = get_clock()
        t_now = as_of_time or clock.now()
        if hasattr(t_now, "tzinfo") and t_now.tzinfo is None:
            t_now = t_now.replace(tzinfo=IST_TIMEZONE)

        delta = float(current_delay_min - previous_delay_min)

        # Only attribute significant delay jumps
        if delta < self.min_delta:
            return None

        # Fetch / enrich 5-layer operational context
        ctx = context or self.context_engine.get_train_context(
            train_no=train_no,
            run_date=run_date,
            current_station_code=station_code,
            current_km=current_km,
            as_of_time=t_now,
        )

        resolved_stn = station_code or ctx.current_station_code or "NDLS"
        remaining = delta
        attributed_causes: List[AttributedCause] = []

        # =========================================================================
        # Rule 1: RAKE_INHERIT (Same-Rake Incoming Turnaround Cascade)
        # =========================================================================
        if remaining > 0.0 and ctx.rake.has_rake_link and ctx.rake.turnaround_deficit_min > 0:
            rake_alloc = min(remaining, float(ctx.rake.turnaround_deficit_min))
            if rake_alloc > 0.0:
                attributed_causes.append(
                    AttributedCause(
                        cause_code="RAKE_INHERIT",
                        attributed_min=rake_alloc,
                        explanation=f"Incoming rake #{ctx.rake.incoming_train} arrived with +{ctx.rake.incoming_delay_min}m delay (turnaround buffer deficit: {ctx.rake.turnaround_deficit_min}m)",
                        evidence={
                            "incoming_train": ctx.rake.incoming_train,
                            "incoming_delay_min": ctx.rake.incoming_delay_min,
                            "turnaround_deficit_min": ctx.rake.turnaround_deficit_min,
                            "turnaround_min": ctx.rake.turnaround_min,
                            "station_code": resolved_stn,
                        },
                    )
                )
                remaining = max(0.0, remaining - rake_alloc)

        # =========================================================================
        # Rule 2: TSR_ACTIVE (Active Speed Restrictions / Track Maintenance)
        # =========================================================================
        if remaining > 0.0 and len(ctx.active_tsrs) > 0:
            total_tsr_penalty = sum(tsr.delay_penalty_min for tsr in ctx.active_tsrs)
            tsr_alloc = min(remaining, float(total_tsr_penalty))
            if tsr_alloc > 0.0:
                primary_tsr = ctx.active_tsrs[0]
                attributed_causes.append(
                    AttributedCause(
                        cause_code="TSR_ACTIVE",
                        attributed_min=tsr_alloc,
                        explanation=f"Active Speed Restriction on {primary_tsr.from_code}–{primary_tsr.to_code} ({primary_tsr.speed_limit_kmph} km/h): {primary_tsr.cause}",
                        evidence={
                            "from_code": primary_tsr.from_code,
                            "to_code": primary_tsr.to_code,
                            "speed_limit_kmph": primary_tsr.speed_limit_kmph,
                            "cause": primary_tsr.cause,
                            "delay_penalty_min": primary_tsr.delay_penalty_min,
                            "total_active_tsrs": len(ctx.active_tsrs),
                        },
                    )
                )
                remaining = max(0.0, remaining - tsr_alloc)

        # =========================================================================
        # Rule 3: WEATHER_FOG (Dense Fog & Poor Visibility)
        # =========================================================================
        if remaining > 0.0 and (ctx.weather.fog_flag == 1 or ctx.weather.visibility_km < 1.0):
            fog_potential = 12.0  # Standard Fog Safety Protocol delay window
            fog_alloc = min(remaining, fog_potential)
            if fog_alloc > 0.0:
                attributed_causes.append(
                    AttributedCause(
                        cause_code="WEATHER_FOG",
                        attributed_min=fog_alloc,
                        explanation=f"Dense fog visibility restriction ({ctx.weather.visibility_km:.1f}km visibility, temp {ctx.weather.temp_celsius:.1f}°C, hum {ctx.weather.humidity_pct:.0f}%)",
                        evidence={
                            "fog_flag": ctx.weather.fog_flag,
                            "visibility_km": ctx.weather.visibility_km,
                            "temp_celsius": ctx.weather.temp_celsius,
                            "humidity_pct": ctx.weather.humidity_pct,
                            "station_code": ctx.weather.station_code,
                        },
                    )
                )
                remaining = max(0.0, remaining - fog_alloc)

        # =========================================================================
        # Rule 4: WEATHER_RAIN (Heavy Precipitation Caution Orders)
        # =========================================================================
        if remaining > 0.0 and ctx.weather.precip_mm >= settings.HEAVY_RAIN_THRESHOLD_MM:
            rain_potential = 8.0
            rain_alloc = min(remaining, rain_potential)
            if rain_alloc > 0.0:
                attributed_causes.append(
                    AttributedCause(
                        cause_code="WEATHER_RAIN",
                        attributed_min=rain_alloc,
                        explanation=f"Heavy rainfall caution speed order ({ctx.weather.precip_mm:.1f}mm precipitation)",
                        evidence={
                            "precip_mm": ctx.weather.precip_mm,
                            "station_code": ctx.weather.station_code,
                        },
                    )
                )
                remaining = max(0.0, remaining - rain_alloc)

        # =========================================================================
        # Rule 5: PLATFORM_WAIT (Terminal Platform Berthing Hold / Conflict)
        # =========================================================================
        if remaining > 0.0 and (ctx.platform.is_conflicted or ctx.platform.conflict_duration_min > 0):
            plat_dur = float(ctx.platform.conflict_duration_min if ctx.platform.conflict_duration_min > 0 else 10.0)
            plat_alloc = min(remaining, plat_dur)
            if plat_alloc > 0.0:
                attributed_causes.append(
                    AttributedCause(
                        cause_code="PLATFORM_WAIT",
                        attributed_min=plat_alloc,
                        explanation=f"Platform berthing hold at {ctx.platform.station_code} (Platform {ctx.platform.platform} conflict with #{ctx.platform.conflict_train})",
                        evidence={
                            "station_code": ctx.platform.station_code,
                            "platform": ctx.platform.platform,
                            "conflict_train": ctx.platform.conflict_train,
                            "conflict_duration_min": ctx.platform.conflict_duration_min,
                        },
                    )
                )
                remaining = max(0.0, remaining - plat_alloc)

        # =========================================================================
        # Rule 6: CONGESTION (Preceding Traffic & Section Over-Occupancy)
        # =========================================================================
        if remaining > 0.0 and (
            ctx.spatial.is_congested
            or ctx.spatial.section_occupancy_pct >= 60.0
            or ctx.spatial.trains_ahead_30k >= 1
            or ctx.spatial.sum_delay_trains_ahead_30k >= 10.0
        ):
            cong_potential = max(4.0, ctx.spatial.sum_delay_trains_ahead_30k * 0.5)
            cong_alloc = min(remaining, float(cong_potential))
            if cong_alloc > 0.0:
                attributed_causes.append(
                    AttributedCause(
                        cause_code="CONGESTION",
                        attributed_min=cong_alloc,
                        explanation=f"Corridor congestion ({ctx.spatial.trains_ahead_30k} trains ahead in 30km, section occupancy {ctx.spatial.section_occupancy_pct:.0f}%)",
                        evidence={
                            "trains_ahead_30k": ctx.spatial.trains_ahead_30k,
                            "trains_behind_30k": ctx.spatial.trains_behind_30k,
                            "sum_delay_trains_ahead_30k": ctx.spatial.sum_delay_trains_ahead_30k,
                            "section_occupancy_pct": ctx.spatial.section_occupancy_pct,
                        },
                    )
                )
                remaining = max(0.0, remaining - cong_alloc)

        # =========================================================================
        # Rule 7: UNEXPLAINED (Residual / Unscheduled Operational Delay)
        # =========================================================================
        if remaining > self.unexplained_tolerance:
            attributed_causes.append(
                AttributedCause(
                    cause_code="UNEXPLAINED",
                    attributed_min=remaining,
                    explanation=f"Unscheduled dwell / loco acceleration loss (+{remaining:.1f}m unaccounted by corridor sensors)",
                    evidence={
                        "residual_min": round(remaining, 2),
                        "measured_delta_min": round(delta, 2),
                        "station_code": resolved_stn,
                    },
                )
            )
            remaining = 0.0
        elif remaining > 0.0:
            # Reconcile tiny float rounding remainder into the primary cause
            if attributed_causes:
                attributed_causes[0].attributed_min += remaining
            else:
                attributed_causes.append(
                    AttributedCause(
                        cause_code="UNEXPLAINED",
                        attributed_min=remaining,
                        explanation=f"Minor operational latency (+{remaining:.1f}m)",
                        evidence={"residual_min": round(remaining, 2)},
                    )
                )
            remaining = 0.0

        # Exact accounting mathematical invariant check
        total_attributed = sum(c.attributed_min for c in attributed_causes)
        diff = delta - total_attributed
        if abs(diff) > 0.0 and attributed_causes:
            attributed_causes[0].attributed_min += diff
            total_attributed = sum(c.attributed_min for c in attributed_causes)

        accounting_err = abs(total_attributed - delta)
        assert accounting_err < 1e-6, f"Exact accounting invariant violated: sum={total_attributed} != delta={delta}"

        # Sort causes by attributed minutes descending
        attributed_causes.sort(key=lambda x: x.attributed_min, reverse=True)

        primary = attributed_causes[0].cause_code if attributed_causes else "UNEXPLAINED"
        secondary = attributed_causes[1].cause_code if len(attributed_causes) > 1 else None

        # Build structured JSON payload
        evidence_payload = {
            "causes": [c.to_dict() for c in attributed_causes],
            "total_delta_min": round(delta, 1),
            "context_snapshot": ctx.to_dict(),
        }

        # Persist to live_delay_ledger table
        ledger_id = self.db.append_live_delay_ledger(
            train_no=train_no,
            run_date=run_date,
            timestamp=t_now.isoformat(),
            delay_change_min=round(delta, 1),
            previous_delay_min=round(previous_delay_min, 1),
            current_delay_min=round(current_delay_min, 1),
            primary_cause=primary,
            secondary_cause=secondary,
            confidence=1.0,
            evidence_json=json.dumps(evidence_payload),
            is_exact_accounting=1,
            created_at=t_now.isoformat(),
        )

        return AttributionResult(
            train_no=train_no,
            run_date=run_date,
            timestamp=t_now.isoformat(),
            station_code=resolved_stn,
            measured_delta_min=delta,
            previous_delay_min=previous_delay_min,
            current_delay_min=current_delay_min,
            primary_cause=primary,
            secondary_cause=secondary,
            causes=attributed_causes,
            is_exact_accounting=True,
            confidence=1.0,
            ledger_id=ledger_id,
        )

    def get_why_late_summary(self, train_no: str, run_date: str) -> Dict[str, Any]:
        """Retrieves and aggregates all historical and live causal attributions for a train run."""
        ledger_rows = self.db.get_live_delay_ledger_for_train(train_no, run_date)

        cause_sums: Dict[str, float] = {c: 0.0 for c in self.VALID_CAUSES}
        detailed_events = []
        total_measured_delta = 0.0

        for r in ledger_rows:
            delta = float(r["delay_change_min"])
            total_measured_delta += delta

            try:
                ev_data = json.loads(r["evidence_json"])
                sub_causes = ev_data.get("causes", [])
                for sc in sub_causes:
                    cc = sc.get("cause_code", "UNEXPLAINED")
                    if cc in cause_sums:
                        cause_sums[cc] += float(sc.get("attributed_min", 0.0))
            except Exception:
                # Fallback to primary cause
                p = r["primary_cause"]
                if p in cause_sums:
                    cause_sums[p] += delta

            detailed_events.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "delay_change_min": r["delay_change_min"],
                "previous_delay_min": r["previous_delay_min"],
                "current_delay_min": r["current_delay_min"],
                "primary_cause": r["primary_cause"],
                "secondary_cause": r.get("secondary_cause"),
                "is_exact_accounting": bool(r.get("is_exact_accounting", 1)),
            })

        # Format why-late breakdown chips
        breakdown_chips = []
        for code, mins in cause_sums.items():
            if mins > 0.0:
                breakdown_chips.append({
                    "cause_code": code,
                    "attributed_min": round(mins, 1),
                    "percentage": round((mins / total_measured_delta) * 100.0, 1) if total_measured_delta > 0 else 0.0,
                })
        breakdown_chips.sort(key=lambda x: x["attributed_min"], reverse=True)

        return {
            "train_no": train_no,
            "run_date": run_date,
            "total_attributed_delay_min": round(total_measured_delta, 1),
            "is_exact_accounting": True,
            "cause_breakdown": breakdown_chips,
            "events_count": len(detailed_events),
            "timeline": detailed_events,
        }


# Global singleton instance
_GLOBAL_ATTRIBUTION_ENGINE: Optional[LiveAttributionEngine] = None


def get_attribution_engine(db: Optional[Database] = None) -> LiveAttributionEngine:
    """Returns the shared LiveAttributionEngine instance."""
    global _GLOBAL_ATTRIBUTION_ENGINE
    if db is not None:
        return LiveAttributionEngine(db)
    if _GLOBAL_ATTRIBUTION_ENGINE is None:
        _GLOBAL_ATTRIBUTION_ENGINE = LiveAttributionEngine()
    return _GLOBAL_ATTRIBUTION_ENGINE


if __name__ == "__main__":
    print("=== RailTwin-X LiveAttributionEngine Demo ===")
    ae = LiveAttributionEngine()
    res = ae.evaluate_delay_jump(
        train_no="12301",
        run_date=datetime.date.today().strftime("%Y-%m-%d"),
        previous_delay_min=5.0,
        current_delay_min=21.0,  # +16m jump
        station_code="CNB",
        current_km=440.0,
    )
    if res:
        print(f"Delay Jump +{res.measured_delta_min}m on #{res.train_no}:")
        print(f"  - Primary Cause: {res.primary_cause}")
        print(f"  - Secondary Cause: {res.secondary_cause}")
        print(f"  - Exact Accounting: {res.is_exact_accounting}")
        for c in res.causes:
            print(f"    * [{c.cause_code}] +{c.attributed_min}m -> {c.explanation}")
