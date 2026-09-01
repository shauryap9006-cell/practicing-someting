"""Environment snapshot -> control-room/23_DIAGNOSTICS/00_env.txt"""
import sys, os, platform, subprocess
from pathlib import Path

OUT = Path("control-room/23_DIAGNOSTICS"); OUT.mkdir(parents=True, exist_ok=True)
L = []
def p(s=""): L.append(str(s)); print(s)

p("=== ENV SNAPSHOT ===")
p(f"python        : {sys.version}")
p(f"platform      : {platform.platform()}")
p(f"cwd           : {os.getcwd()}")
p(f"PYTHONHASHSEED: {os.environ.get('PYTHONHASHSEED', '<unset> => hash() RANDOMIZED per process')}")
for mod in ("torch", "numpy", "scipy", "pandas", "lightgbm", "sklearn"):
    try:
        m = __import__(mod); p(f"{mod:14s}: {getattr(m, '__version__', '?')}")
    except Exception as e:
        p(f"{mod:14s}: IMPORT FAIL {e}")

p("\n=== requirements.txt vs installed ===")
import importlib.metadata as md
if Path("requirements.txt").exists():
    for line in Path("requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
        try: p(f"  {pkg:30s} installed={md.version(pkg)}  pinned={line}")
        except md.PackageNotFoundError: p(f"  {pkg:30s} *** NOT INSTALLED ***  pinned={line}")

p("\n=== git state ===")
for cmd in (["git", "rev-parse", "HEAD"], ["git", "status", "--porcelain"],
            ["git", "log", "-1", "--format=%h %ad %s", "--", "ml/artifacts"],
            ["git", "log", "-1", "--format=%h %ad %s", "--", "ml/artifacts_v2"]):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        p(f"$ {' '.join(cmd)}\n  {r.stdout.strip() or r.stderr.strip()}")
    except Exception as e: p(f"$ {' '.join(cmd)} FAILED: {e}")

p("\n=== database files ===")
for db in ("data/railtwin.db", "data/railtwin.db.gz"):
    pth = Path(db)
    p(f"{db}: exists={pth.exists()}" + (f" size={pth.stat().st_size:,}" if pth.exists() else ""))

(OUT / "00_env.txt").write_text("\n".join(L), encoding="utf-8")
