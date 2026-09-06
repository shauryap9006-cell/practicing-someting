import os
import sys
import re
from pathlib import Path

ROOT = Path.cwd()
code_dirs = [ROOT / d for d in ['api', 'engine', 'collector', 'data', 'ml', 'safety', 'scripts', 'notifications']]

bg_patterns = [
    (re.compile(r'asyncio\.create_task\s*\('), 'asyncio.create_task'),
    (re.compile(r'threading\.Thread\s*\('), 'threading.Thread'),
    (re.compile(r'multiprocessing\.Process\s*\('), 'multiprocessing.Process'),
    (re.compile(r'loop\.create_task\s*\('), 'loop.create_task'),
    (re.compile(r'BackgroundTasks'), 'FastAPI BackgroundTasks'),
    (re.compile(r'run_in_executor'), 'run_in_executor'),
]

found = []
for cdir in code_dirs:
    if not cdir.exists():
        continue
    for py in cdir.rglob('*.py'):
        try:
            text = py.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        rel = str(py.relative_to(ROOT))
        for line_no, line in enumerate(text.splitlines(), 1):
            for pat, name in bg_patterns:
                if pat.search(line):
                    found.append({
                        'type': name,
                        'file': rel,
                        'line': line_no,
                        'snippet': line.strip()
                    })

for f in found:
    print(f"{f['type']} at {f['file']}:{f['line']} -> {f['snippet']}")

import json
with open('audit_probes/background_tasks.json', 'w') as out:
    json.dump(found, out, indent=2)
