from pathlib import Path

root = Path.cwd()
for p in list(root.glob("api/**/*.py")) + list(root.glob("engine/**/*.py")):
    text = p.read_text(encoding="utf-8", errors="ignore")
    rel = str(p.relative_to(root))
    for idx, line in enumerate(text.splitlines(), 1):
        if "datetime.now()" in line:
            print(f"{rel}:{idx} -> naive datetime.now() without tz: {line.strip()}")
