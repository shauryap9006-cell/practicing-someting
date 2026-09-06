import os
import sys
import re
import json
from pathlib import Path

ROOT = Path.cwd()
art_dir = ROOT / 'ml' / 'artifacts'
files = [f.name for f in art_dir.iterdir() if f.is_file()]

code_dirs = [ROOT / d for d in ['api', 'ml', 'engine', 'scripts', 'data']]

usage = {}
for f in sorted(files):
    usage[f] = []
    for cdir in code_dirs:
        for py in cdir.rglob('*.py'):
            try:
                text = py.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            if f in text:
                rel = str(py.relative_to(ROOT))
                for idx, line in enumerate(text.splitlines(), 1):
                    if f in line:
                        usage[f].append(f'{rel}:{idx}')

with open('audit_probes/artifact_usage.json', 'w') as out:
    json.dump(usage, out, indent=2)

for f, locs in usage.items():
    print(f'{f} ({len(locs)} refs): {locs[:3]}')
