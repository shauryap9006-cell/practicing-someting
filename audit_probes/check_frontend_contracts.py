import os
import sys
import re
import json
from pathlib import Path

ROOT = Path.cwd()
web_src = ROOT / 'web' / 'src'

url_patterns = [
    re.compile(r'apiClient\.(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[\'\"]([^\'\"\?]+)', re.IGNORECASE),
    re.compile(r'fetch\s*\(\s*[\'\"]([^\'\"\?]+)', re.IGNORECASE),
    re.compile(r'axios\.(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[\'\"]([^\'\"\?]+)', re.IGNORECASE),
    re.compile(r'[\'\"](\/(?:v1|api)\/[a-zA-Z0-9_\-\/\{\}\$]+)[\'\"]'),
    re.compile(r'(\/(?:v1|api)\/[^]+)'),
]

found_calls = []
for ts_file in web_src.rglob('*.*'):
    if ts_file.suffix not in ('.ts', '.tsx', '.js', '.jsx'):
        continue
    try:
        text = ts_file.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    rel = str(ts_file.relative_to(ROOT))
    for line_no, line in enumerate(text.splitlines(), 1):
        for pat in url_patterns:
            for match in pat.finditer(line):
                groups = match.groups()
                if len(groups) == 2:
                    method, url = groups[0].upper(), groups[1]
                else:
                    method, url = 'UNKNOWN', groups[0]
                found_calls.append({
                    'file': rel,
                    'line': line_no,
                    'method': method,
                    'url': url.strip(),
                    'raw': line.strip()
                })

unique_urls = {}
for c in found_calls:
    key = (c['method'], c['url'])
    if key not in unique_urls:
        unique_urls[key] = []
    unique_urls[key].append(c['file'] + ':' + str(c['line']))

print(f'Total frontend API calls found: {len(found_calls)}')
print(f'Total unique (method, url) endpoints: {len(unique_urls)}')

with open('audit_probes/frontend_calls.json', 'w') as out:
    json.dump({'total_calls': len(found_calls), 'unique_endpoints': [{'method': m, 'url': u, 'call_sites': locs} for (m, u), locs in sorted(unique_urls.items())]}, out, indent=2)

for (m, u), locs in sorted(unique_urls.items())[:25]:
    print(f'{m:7} {u} ({len(locs)} sites: {locs[0]})')
