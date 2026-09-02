from __future__ import annotations
import datetime, json, os, pytest
from api.predictor import get_predictor_service
from engine.clocks import ReplayClock, set_global_clock, RealClock
from data.db import get_db

def test_t82_differential_dynamism_full_cycle():
    db = get_db()
    clock = ReplayClock("2026-08-27T08:00:00+05:30")
    set_global_clock(clock)
    predictor = get_predictor_service()
    train_no = "12034"
    target_stn = "NDLS"

    try:
        with db.transaction() as cur:
            cur.execute("UPDATE speed_restrictions SET is_active = 0;")

        # (a) Baseline A
        t0 = clock.now_iso()
        res_a = predictor.predict_train_eta(train_no, target_stn)
        eta_a = res_a["predicted_delay_min"]

        # (b) Advance clock 10 min without events -> ETA B
        clock.advance(10.0)
        t1 = clock.now_iso()
        res_b = predictor.predict_train_eta(train_no, target_stn)
        eta_b = res_b["predicted_delay_min"]
        assert eta_b == eta_a, f"ETA B ({eta_b}) must equal baseline A ({eta_a})"

        # (c) Inject TSR on next section -> ETA C
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO speed_restrictions (from_code, to_code, speed_limit_kmph, cause, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("GZB", "NDLS", 30.0, "Emergency Track Fracture at Sahibabad", 1, t1),
            )
            tsr_id = cur.lastrowid

        res_c = predictor.predict_train_eta(train_no, target_stn)
        eta_c = res_c["predicted_delay_min"]
        assert eta_c > eta_b + 5, f"ETA C ({eta_c}) must be > B+5 ({eta_b + 5})"

        # (d) Advance clock 5 min with TSR active -> ETA D
        clock.advance(5.0)
        t2 = clock.now_iso()
        res_d = predictor.predict_train_eta(train_no, target_stn)
        eta_d = res_d["predicted_delay_min"]
        assert eta_d == eta_c, f"ETA D ({eta_d}) must equal ETA C ({eta_c})"

        # (e) Clear TSR -> ETA E
        with db.transaction() as cur:
            cur.execute("UPDATE speed_restrictions SET is_active = 0 WHERE id = ?", (tsr_id,))

        res_e = predictor.predict_train_eta(train_no, target_stn)
        eta_e = res_e["predicted_delay_min"]
        assert eta_e < eta_c, f"ETA E ({eta_e}) must drop below C ({eta_c})"

        # Write proof artifact
        os.makedirs("audit", exist_ok=True)
        proof = {
            "test_id": "T8.2",
            "title": "Differential Dynamism Proof Transcript",
            "train_no": train_no,
            "target_station": target_stn,
            "step_a_baseline": {"clock": t0, "delay_min": eta_a},
            "step_b_clock_advance_no_events": {"clock": t1, "delay_min": eta_b, "equals_a": True},
            "step_c_tsr_injected": {"clock": t1, "delay_min": eta_c, "greater_than_b_plus_5": True, "delta_min": eta_c - eta_b},
            "step_d_clock_advance_tsr_active": {"clock": t2, "delay_min": eta_d, "equals_c": True},
            "step_e_tsr_cleared": {"clock": t2, "delay_min": eta_e, "dropped_below_c": True, "returned_to_baseline": eta_e == eta_a},
            "verdict": "PASS",
        }
        with open("audit/T82_dynamism_proof.json", "w", encoding="utf-8") as pf:
            json.dump(proof, pf, indent=2)

    finally:
        set_global_clock(RealClock())
