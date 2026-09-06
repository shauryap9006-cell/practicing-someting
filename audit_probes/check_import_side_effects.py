import sys
import sqlite3
import socket
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'docs'))

db_connect_calls = []
orig_connect = sqlite3.connect
def logged_connect(*args, **kwargs):
    import traceback
    stack = traceback.format_stack()
    db_connect_calls.append((args, stack[-2]))
    return orig_connect(*args, **kwargs)

sqlite3.connect = logged_connect

print('[PROBE] Importing api.main...')
import api.main
print(f'[PROBE] Import completed. Total sqlite3.connect calls during import: {len(db_connect_calls)}')
for idx, (args, caller) in enumerate(db_connect_calls):
    print(f'  Call {idx+1}: {args[0] if args else kwargs}')
    print(f'    Caller: {caller.strip()}')
