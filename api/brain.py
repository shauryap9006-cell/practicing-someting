"""RailTwin-X Brain Orchestrator & Advisory Pipeline (Phase G6).

Integrates:
1. State Perception & Feature Vector Construction
2. Ensemble ML / Champion Inference (Phase G1-G3)
3. 100% Deterministic Safety Interlock Validation (Phase G4)
4. 100% Deterministic Conflict Scanner (Phase G5)
5. Structured Advisory Action Formulator (Advisory only, human_ack_required = True)
6. Append-Only Audit Logging (brain_advisory_audit table)
"""

from __future__ import annotations

import datetime
import json
import time
from typing import Any, Dict, List, Optional
import pandas as pd

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock
from engine.conflicts import ConflictScanner
from engine.track_graph import TrackGraph
from ml.ensemble import EnsemblePredictor
from ml.features import FEATURE_NAMES, TrainFeatureVector
from ml.snapshots import SnapshotGenerator
from safety.interlock import validate_prediction_through_interlock, SafetyInterlockReport


class BrainOrchestrator:
    """Central decision advisory orchestrator."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self.track_graph = TrackGraph(self.db)
        self.snapshot_gen = SnapshotGenerator(self.db)
        self.ensemble = EnsemblePredictor(self.db)
        self.conflict_scanner = ConflictScanner(self.db)

    def advise(
        self,
        train_no: str,
        target_station_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the complete end-to-end perception -> inference -> safety interlock -> conflict scan pipeline."""
        t_start = time.perf_counter()
        clock = get_clock()
        now_iso = clock.now_iso()
        today_str = clock.today_str()

        route = self.track_graph.get_route(train_no)
        if not route:
            return {
                "train_no": train_no,
                "status": "NOT_FOUND",
                "message": f"Train {train_no} not registered in network.",
                "confidence_tier": "LOW",
                "human_ack_required": True,
                "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 2),
            }

        # 1. Gather latest state
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT seq, station_code, delay_arr_min, delay_dep_min, sched_arr, sched_dep
                FROM station_events
                WHERE train_no = ?
                ORDER BY run_date DESC, seq DESC LIMIT 1
                """,
                (train_no,),
            )
            latest_ev = cur.fetchone()

        # Target station
        if target_station_code:
            target_stop = next((s for s in route if s["station_code"] == target_station_code.upper()), route[-1])
        else:
            target_stop = route[-1]

        target_stn = target_stop["station_code"]
        target_seq = int(target_stop["seq"])

        # Cold start / no live data path (Honest degradation)
        if not latest_ev:
            c_seq = 1
            c_delay = 0.0
            p_delay = 0.0
            base_tier = "LOW"
        else:
            c_seq = int(latest_ev["seq"])
            c_delay = float(latest_ev["delay_arr_min"] if latest_ev["delay_arr_min"] is not None else (latest_ev["delay_dep_min"] or 0.0))
            p_delay = c_delay
            base_tier = "HIGH"

        # 2. Extract Feature Vector
        try:
            vec = self.snapshot_gen.extract_features_at_snapshot(
                train_no=train_no,
                current_seq=c_seq,
                target_seq=target_seq,
                run_date_str=today_str,
                current_delay=c_delay,
                prev_delay=p_delay,
                query_time_iso=now_iso,
            )
            feat_dict = vec.to_dict()
            feat_df = pd.DataFrame([feat_dict])
        except Exception as e:
            feat_dict = {
                "current_delay": c_delay,
                "km_remaining": max(0.0, float(target_stop["distance_km"]) - float(route[c_seq-1]["distance_km"])),
                "hops_remaining": max(0, target_seq - c_seq),
            }
            feat_df = pd.DataFrame([feat_dict])

        # 3. Model Prediction (Ensemble Blend)
        raw_p10, raw_p50, raw_p90 = self.ensemble.predict(feat_df)

        # 4. Safety Interlock Validation (100% Deterministic)
        interlock_report = validate_prediction_through_interlock(
            features=feat_dict,
            raw_p10=raw_p10,
            raw_p50=raw_p50,
            raw_p90=raw_p90,
            base_tier=base_tier,
        )

        # 5. Deterministic Conflict Scan
        conflicts = self.conflict_scanner.scan_train_conflicts(train_no, target_date_str=today_str)
        high_severity_confs = [c for c in conflicts if c.severity == "HIGH"]

        # 6. Action Formulation (Advisory)
        recommendations = []
        if high_severity_confs:
            top_conf = high_severity_confs[0]
            if top_conf.conflict_type == "SINGLE_LINE_OPPOSING":
                recommendations.append({
                    "action_code": "HOLD_AT_LOOP_ADVISORY",
                    "action_name": f"Hold #{train_no} at {top_conf.station_code} loop siding",
                    "reason": top_conf.reason,
                    "target_train": top_conf.with_train,
                    "is_safety_critical": True,
                })
            else:
                recommendations.append({
                    "action_code": "STOP_TRAIN_ADVISORY",
                    "action_name": f"Advisory signal hold before {top_conf.station_code}",
                    "reason": top_conf.reason,
                    "target_train": top_conf.with_train,
                    "is_safety_critical": True,
                })
        elif interlock_report.clamp_applied:
            recommendations.append({
                "action_code": "CONTROLLER_VERIFY_ADVISORY",
                "action_name": "Verify running status with Section Controller",
                "reason": "Safety interlock clamped anomalous ML model prediction output.",
                "is_safety_critical": False,
            })
        else:
            recommendations.append({
                "action_code": "PROCEED_NOMINAL",
                "action_name": "Proceed under nominal Section Controller timetable",
                "reason": "Track context nominal. No spatial conflicts detected.",
                "is_safety_critical": False,
            })

        latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        result_payload = {
            "train_no": train_no,
            "train_name": route[0].get("name", "Express"),
            "target_station": target_stn,
            "sched_arr": target_stop.get("sched_arr"),
            "current_delay_min": int(round(c_delay)),
            "prediction": {
                "best_p10_min": round(interlock_report.clamped_p10, 1),
                "likely_p50_min": round(interlock_report.clamped_p50, 1),
                "worst_p90_min": round(interlock_report.clamped_p90, 1),
            },
            "confidence_tier": interlock_report.confidence_tier,
            "safety_checks": [c.to_dict() for c in interlock_report.checks],
            "all_safety_checks_passed": interlock_report.all_passed,
            "conflicts": [c.to_dict() for c in conflicts],
            "advisory_recommendations": recommendations,
            "human_ack_required": True,
            "model_version": "railtwin-v3-neural-interlock",
            "latency_ms": latency_ms,
            "timestamp": now_iso,
        }

        # 7. Append-only Audit Log
        try:
            with self.db.transaction() as cur:
                cur.execute(
                    """
                    INSERT INTO brain_advisory_audit
                    (train_no, query_timestamp, input_delay_min, predicted_delay_min,
                     confidence_tier, checks_passed, conflicts_count, suggested_action,
                     model_version, raw_payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        train_no,
                        now_iso,
                        c_delay,
                        interlock_report.clamped_p50,
                        interlock_report.confidence_tier,
                        1 if interlock_report.all_passed else 0,
                        len(conflicts),
                        recommendations[0]["action_code"],
                        "railtwin-v3-neural-interlock",
                        json.dumps(result_payload),
                    ),
                )
        except Exception as log_err:
            print(f"[WARN] Failed to write brain audit log: {log_err}")

        # 8. Outbound Alert Dispatch for Safety-Critical Advisories
        if high_severity_confs or any(r.get("is_safety_critical") for r in recommendations):
            try:
                from notifications import AlertEvent, get_dispatcher
                dispatcher = get_dispatcher(self.db)
                top_rec = recommendations[0] if recommendations else {}
                adv_id = f"ADV-{target_stn}-{train_no}"
                dispatcher.dispatch(
                    AlertEvent(
                        severity="HIGH" if high_severity_confs else "MEDIUM",
                        event_type="advisory",
                        title=top_rec.get("action_name", f"Advisory for #{train_no}"),
                        body=top_rec.get("reason", "Operational action required"),
                        station_code=target_stn,
                        train_no=train_no,
                        roles=["controller", "pointsman"],
                        ack_id=adv_id,
                        metadata={"action_code": top_rec.get("action_code"), "target_train": top_rec.get("target_train")},
                    )
                )
            except Exception as disp_err:
                print(f"[WARN] Failed to dispatch advisory alert: {disp_err}")

        return result_payload

