import concurrent.futures
from data.audit import append_audit_entry, verify_audit_log
from data.db import get_db


def test_audit_concurrency():
    db = get_db()
    is_valid, fork_count, initial_count = verify_audit_log(db)
    assert is_valid is True
    assert fork_count == 0

    total_writes = 20
    num_threads = 5

    def write_entry(idx: int):
        return append_audit_entry(
            actor_id=f"worker_{idx}",
            actor_role="controller",
            action="CONCURRENT_UPDATE",
            table_name="speed_restrictions",
            record_id=str(idx),
            before_state={"status": "pending", "idx": idx},
            after_state={"status": "active", "idx": idx},
            db=db,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(write_entry, i) for i in range(total_writes)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == total_writes

    is_valid, fork_count, final_count = verify_audit_log(db)
    assert is_valid is True
    assert fork_count == 0
    assert final_count == initial_count + total_writes
