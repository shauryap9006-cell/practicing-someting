import sqlite3
from pathlib import Path
from data.db import Database, get_db

db = get_db()
conn = db.get_connection()
cur = conn.cursor()

# 4.3 WAL & PRAGMAs
cur.execute("PRAGMA journal_mode;")
journal_mode = cur.fetchone()[0]
cur.execute("PRAGMA busy_timeout;")
busy_timeout = cur.fetchone()[0]
cur.execute("PRAGMA synchronous;")
synchronous = cur.fetchone()[0]

print(f"DB PRAGMAs: journal_mode={journal_mode}, busy_timeout={busy_timeout}ms, synchronous={synchronous}")

# 4.4 Index Coverage & EXPLAIN QUERY PLAN on hot queries
hot_queries = [
    ("station_events lookup", "EXPLAIN QUERY PLAN SELECT * FROM station_events WHERE train_no = '12301' AND station_code = 'CNB' ORDER BY run_date DESC, seq DESC LIMIT 1;"),
    ("ledger ordered scan", "EXPLAIN QUERY PLAN SELECT * FROM eta_prediction_ledger ORDER BY id DESC LIMIT 10;"),
    ("live positions by station", "EXPLAIN QUERY PLAN SELECT * FROM live_positions WHERE current_station_code = 'CNB';"),
    ("live delay ledger by train", "EXPLAIN QUERY PLAN SELECT * FROM live_delay_ledger WHERE train_no = '12301' AND run_date = '2026-08-25' ORDER BY id ASC;"),
    ("audit log scan", "EXPLAIN QUERY PLAN SELECT * FROM audit_log ORDER BY id DESC LIMIT 1;"),
]

print("\nEXPLAIN QUERY PLAN Results for Hot Queries:")
for name, q in hot_queries:
    cur.execute(q)
    plan = cur.fetchall()
    plan_desc = "; ".join([p[3] for p in plan])
    is_scan = "SCAN" in plan_desc and "USING INDEX" not in plan_desc
    flag = "TABLE SCAN (SLOW)" if is_scan else "INDEXED"
    print(f"  [{name}]: {flag} -> {plan_desc}")

# 4.5 Schema-Code Drift for 5 most written tables
tables_to_check = ["station_events", "eta_prediction_ledger", "live_positions", "live_delay_ledger", "audit_log"]
print("\nSchema Columns Inspection for 5 Most Written Tables:")
for tbl in tables_to_check:
    cur.execute(f"PRAGMA table_info('{tbl}');")
    cols = [r[1] for r in cur.fetchall()]
    print(f"  {tbl} ({len(cols)} cols): {cols[:6]}...")

conn.close()
