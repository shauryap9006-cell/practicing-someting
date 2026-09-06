import os
import sys
import re
import sqlite3
import json
from pathlib import Path

ROOT = Path.cwd()
db_path = ROOT / "data" / "railtwin.db"

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name;")
tables_meta = cur.fetchall()

db_tables = {}
for t in tables_meta:
    tbl_name = t['name']
    if tbl_name.startswith('sqlite_'):
        continue
    cur.execute(f"PRAGMA table_info('{tbl_name}');")
    cols = [dict(c) for c in cur.fetchall()]
    cur.execute(f"PRAGMA index_list('{tbl_name}');")
    idx_list = [dict(i) for i in cur.fetchall()]
    for idx in idx_list:
        cur.execute(f"PRAGMA index_info('{idx['name']}');")
        idx['columns'] = [dict(col) for col in cur.fetchall()]
    try:
        cur.execute(f"SELECT COUNT(*) as cnt FROM '{tbl_name}';")
        cnt = cur.fetchone()['cnt']
    except Exception as e:
        cnt = f"error: {e}"
    db_tables[tbl_name] = {
        'columns': cols,
        'indexes': idx_list,
        'row_count': cnt,
        'create_sql': t['sql']
    }

conn.close()

# Scan codebase for table writes: INSERT INTO, UPDATE, DELETE FROM, REPLACE INTO
code_dirs = [ROOT / d for d in ['api', 'engine', 'collector', 'data', 'safety', 'scripts', 'notifications']]
write_patterns = [
    re.compile(r'INSERT\s+(?:OR\s+\w+\s+)?INTO\s+([a-zA-Z0-9_]+)', re.IGNORECASE),
    re.compile(r'UPDATE\s+([a-zA-Z0-9_]+)\s+SET', re.IGNORECASE),
    re.compile(r'DELETE\s+FROM\s+([a-zA-Z0-9_]+)', re.IGNORECASE),
    re.compile(r'REPLACE\s+INTO\s+([a-zA-Z0-9_]+)', re.IGNORECASE)
]

table_writes = {}
for cdir in code_dirs:
    if not cdir.exists():
        continue
    for py_file in cdir.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        rel_path = str(py_file.relative_to(ROOT))
        for line_no, line in enumerate(content.splitlines(), 1):
            for pat in write_patterns:
                for match in pat.finditer(line):
                    tbl = match.group(1).lower()
                    if tbl in ('or', 'set', 'where', 'select', 'null', 'default'):
                        continue
                    if tbl not in table_writes:
                        table_writes[tbl] = []
                    table_writes[tbl].append(f"{rel_path}:{line_no}")

output = {
    'db_tables': list(db_tables.keys()),
    'code_written_tables': list(table_writes.keys()),
    'tables_in_db_not_written_in_code': [t for t in db_tables.keys() if t.lower() not in table_writes],
    'tables_written_in_code_not_in_db': [t for t in table_writes.keys() if t not in db_tables and t.lower() not in [x.lower() for x in db_tables]],
    'details': db_tables,
    'table_writes': table_writes
}

with open('audit_probes/db_schema_inventory.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"Total tables in DB: {len(db_tables)}")
print(f"Total tables written in code: {len(table_writes)}")
print(f"Tables in DB not written in code: {output['tables_in_db_not_written_in_code']}")
print(f"Tables written in code not in DB: {output['tables_written_in_code_not_in_db']}")
