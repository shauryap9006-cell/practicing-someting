from pathlib import Path
import re, json

root = Path('web/src')
endpoints = []

for p in root.rglob('*'):
    if p.suffix in ('.ts', '.tsx', '.js', '.jsx'):
        text = p.read_text(encoding='utf-8', errors='ignore')
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r'[\'"`]((?:/v1|/api)/[^\'"`?\s]+)[\'"`]', line):
                url = m.group(1)
                method = 'GET'
                line_lower = line.lower()
                if 'post' in line_lower:
                    method = 'POST'
                elif 'put' in line_lower:
                    method = 'PUT'
                elif 'delete' in line_lower:
                    method = 'DELETE'
                elif 'patch' in line_lower:
                    method = 'PATCH'
                endpoints.append({'file': str(p), 'line': line_no, 'url': url, 'method': method})

dedup = {}
for e in endpoints:
    key = (e['method'], e['url'])
    dedup.setdefault(key, []).append(f"{e['file']}:{e['line']}")

print(f"Total endpoints found in frontend: {len(endpoints)}")
print(f"Unique (method, url) endpoints: {len(dedup)}")

output = [{'method': m, 'url': u, 'calls': locs} for (m, u), locs in sorted(dedup.items())]
with open('audit_probes/frontend_contracts.json', 'w') as f:
    json.dump(output, f, indent=2)

for item in output:
    print(f"{item['method']:6} {item['url']} ({len(item['calls'])} calls, e.g. {item['calls'][0]})")
