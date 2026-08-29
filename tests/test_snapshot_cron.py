"""RailTwin-X Bucket C Snapshot Collector Test Suite (ASSETS.md §2).

Verifies continuous snapshot capture into `train_runs` and `run_snapshots` with explicit
data provenance labels (rapidapi | synthetic | manual).
"""

from collector.snapshot_cron import SnapshotCollector
from data.db import Database, get_db


def test_snapshot_collector_records_data():
    """Verifies that snapshot cycle creates train_runs and appends run_snapshots."""
    db = get_db()
    collector = SnapshotCollector(db=db)
    summary = collector.record_snapshot_cycle(train_limit=5)

    assert summary["trains_checked"] > 0
    assert summary["snapshots_recorded"] > 0

    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) FROM train_runs;")
        runs_count = cur.fetchone()[0]
        assert runs_count > 0

        cur.execute("SELECT COUNT(*) FROM run_snapshots;")
        snaps_count = cur.fetchone()[0]
        assert snaps_count > 0

        # Check explicit source label
        cur.execute("SELECT DISTINCT source FROM run_snapshots;")
        sources = [r[0] for r in cur.fetchall()]
        for s in sources:
            assert s in ("rapidapi", "synthetic", "manual")
