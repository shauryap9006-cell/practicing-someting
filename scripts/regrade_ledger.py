"""scripts/regrade_ledger.py — Gate 3.4 Branch A: Reset polluted ledger grades.

Resets the 544 polluted rows where actual_delay = 0.0 at target_station = 'GZB',
returning them to un-graded state (actual_delay = NULL, actual_timestamp = NULL,
error_min = NULL, in_band = NULL, winkler_score = NULL).
Because these graded fields are OUTSIDE the block hash, the SHA-256 chain integrity
is preserved unbroken before and after.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.db import Database, get_db
from engine.prediction_ledger import PredictionLedger


def regrade_ledger(db: Database) -> int:
    with db.transaction() as cur:
        cur.execute(
            """
            UPDATE eta_prediction_ledger
            SET actual_delay = NULL,
                actual_timestamp = NULL,
                error_min = NULL,
                in_band = NULL,
                winkler_score = NULL
            WHERE actual_delay = 0.0 AND target_station = 'GZB';
            """
        )
        return cur.rowcount


def main():
    db = get_db()
    ledger = PredictionLedger(db)

    print("=" * 70)
    print("GATE 3.4: REGRADE PREDICTION LEDGER (BRANCH A)")
    print("=" * 70)

    pre_valid, pre_count, pre_broken = ledger.verify_chain_integrity()
    print(
        f"[PRE-CHECK] Integrity valid: {pre_valid} (verified {pre_count} blocks, broken: {pre_broken})"
    )
    assert pre_valid, "Ledger integrity check failed before regrading!"

    with db.transaction() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM eta_prediction_ledger WHERE actual_delay = 0.0 AND target_station = 'GZB';"
        )
        polluted_count = cur.fetchone()[0]
    print(f"[AUDIT] Found {polluted_count} polluted rows (actual_delay=0.0 at GZB)")

    updated = regrade_ledger(db)
    print(f"[UPDATE] Reset {updated} polluted rows to NULL.")

    post_valid, post_count, post_broken = ledger.verify_chain_integrity()
    print(
        f"[POST-CHECK] Integrity valid: {post_valid} (verified {post_count} blocks, broken: {post_broken})"
    )
    assert post_valid, "Ledger integrity check failed after regrading!"
    assert post_count >= pre_count, f"Block count decreased! {post_count} < {pre_count}"

    print("[SUCCESS] Gate 3.4 Branch A completed successfully. Chain intact.")


if __name__ == "__main__":
    main()
