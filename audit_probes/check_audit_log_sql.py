from data.db import get_db
db = get_db()
cur = db.get_connection().cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE name='audit_log'")
print(cur.fetchone()[0])
