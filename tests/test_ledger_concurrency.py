"""Concurrency test for RailTwin-X SHA-256 Prediction Ledger.

Spawns 8 concurrent threads × 20 appends each (160 total concurrent writes),
asserts that no race condition forks the hash chain, all receipts are stored,
and verify_chain_integrity() confirms an unbroken cryptographic chain.
"""
from __future__ import annotations

import concurrent.futures
import pytest

from data.db import get_db
from engine.prediction_ledger import PredictionLedger


def test_ledger_high_concurrency_race_condition():
    """Spawns 8 threads x 20 appends; asserts chain valid, no forks, unbroken chain."""
    db = get_db()
    ledger = PredictionLedger(db)

    # Record initial state
    is_valid_init, init_count, _ = ledger.verify_chain_integrity()
    assert is_valid_init is True, "Ledger must be valid before starting concurrency test"

    num_threads = 8
    appends_per_thread = 20
    expected_new_blocks = num_threads * appends_per_thread

    def worker_append(thread_id: int) -> list[str]:
        receipts = []
        for i in range(appends_per_thread):
            t_no = f"THR-{thread_id:02d}"
            stn = "CNB"
            p10 = float(5 + i)
            p50 = float(10 + i)
            p90 = float(20 + i)
            q_ts = f"2026-09-05T01:{thread_id:02d}:{i:02d}.000000+05:30"
            receipt_hash = ledger.record_prediction_receipt(
                train_no=t_no,
                target_station=stn,
                p10=p10,
                p50=p50,
                p90=p90,
                query_timestamp=q_ts,
            )
            receipts.append(receipt_hash)
        return receipts

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_append, t_id) for t_id in range(num_threads)]
        all_receipts = []
        for f in concurrent.futures.as_completed(futures):
            all_receipts.extend(f.result())

    assert len(all_receipts) == expected_new_blocks
    assert len(set(all_receipts)) == expected_new_blocks, "All receipt hashes must be unique"

    # Verify chain integrity after all concurrent appends
    is_valid_post, post_count, broken_id = ledger.verify_chain_integrity()
    assert is_valid_post is True, f"Hash chain broken at ID {broken_id} after concurrent writes!"
    assert post_count == init_count + expected_new_blocks
    assert broken_id is None
