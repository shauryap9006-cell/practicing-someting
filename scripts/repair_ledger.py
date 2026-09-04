"""scripts/repair_ledger.py — Cryptographic Hash-Chain Repair Utility.

Walks the eta_prediction_ledger from genesis to tip in id order, recomputes
each block hash from canonical stored fields, resolves any concurrency-forked
branches into a linear unbroken SHA-256 hash chain, and prints an idempotent
before/after diff of all repaired blocks.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.db import Database, get_db
from engine.prediction_ledger import GENESIS_HASH, PredictionLedger


def repair_ledger(db: Database) -> list[dict]:
    """Walks the prediction ledger, re-links prev_hash and recomputes receipt_hash.

    Returns a list of diff dicts for all repaired blocks. Idempotent.
    """
    diffs = []
    expected_prev = GENESIS_HASH

    with db.transaction() as cur:
        cur.execute("SELECT * FROM eta_prediction_ledger ORDER BY id ASC;")
        rows = cur.fetchall()

        for idx, r in enumerate(rows):
            r_id = r["id"]
            old_prev = r["prev_hash"]
            old_hash = r["receipt_hash"]

            # Canonical raw block representation
            p10 = float(r["p10_delay"])
            p50 = float(r["p50_delay"])
            p90 = float(r["p90_delay"])
            raw_block = f"{expected_prev}:{r['train_no']}:{r['target_station']}:{p10:.2f}:{p50:.2f}:{p90:.2f}:{r['query_timestamp']}"
            computed_hash = hashlib.sha256(raw_block.encode("utf-8")).hexdigest()

            if old_prev != expected_prev or old_hash != computed_hash:
                diffs.append({
                    "block_id": r_id,
                    "train_no": r["train_no"],
                    "station": r["target_station"],
                    "old_prev": old_prev[:12] + "...",
                    "new_prev": expected_prev[:12] + "...",
                    "old_hash": old_hash[:12] + "...",
                    "new_hash": computed_hash[:12] + "...",
                })
                cur.execute(
                    "UPDATE eta_prediction_ledger SET prev_hash = ?, receipt_hash = ? WHERE id = ?;",
                    (expected_prev, computed_hash, r_id),
                )

            expected_prev = computed_hash

    return diffs


def main():
    parser = argparse.ArgumentParser(description="Repair RailTwin-X prediction ledger hash chain.")
    parser.add_argument("--db-path", type=str, default=None, help="Path to railtwin.db")
    args = parser.parse_args()

    db = Database(args.db_path) if args.db_path else get_db()
    ledger = PredictionLedger(db)

    print("=" * 70)
    print("RAILTWIN-X SHA-256 PREDICTION LEDGER INTEGRITY AUDIT & REPAIR")
    print("=" * 70)

    pre_valid, pre_count, pre_broken = ledger.verify_chain_integrity()
    print(f"[PRE-CHECK] Integrity valid: {pre_valid} (verified {pre_count} blocks, broken at ID: {pre_broken})")

    diffs = repair_ledger(db)

    if diffs:
        print(f"\n[REPAIR] Repaired {len(diffs)} blocks:")
        print(f"{'Block ID':<10} {'Train':<8} {'Station':<8} {'Prev Hash (Old -> New)':<32} {'Block Hash (Old -> New)':<32}")
        print("-" * 90)
        for d in diffs:
            prev_diff = f"{d['old_prev']} -> {d['new_prev']}"
            hash_diff = f"{d['old_hash']} -> {d['new_hash']}"
            print(f"{d['block_id']:<10} {d['train_no']:<8} {d['station']:<8} {prev_diff:<32} {hash_diff:<32}")
    else:
        print("\n[REPAIR] No repairs needed. Ledger is already cryptographically intact.")

    post_valid, post_count, post_broken = ledger.verify_chain_integrity()
    print("\n" + "=" * 70)
    print(f"[POST-CHECK] Integrity valid: {post_valid} (total blocks verified: {post_count}, broken: {post_broken})")
    print("=" * 70)

    if not post_valid:
        print("[FAIL] Post-repair verification failed!", file=sys.stderr)
        sys.exit(1)
    print("[SUCCESS] SHA-256 hash-chained audit ledger verified unbroken.")


if __name__ == "__main__":
    main()
