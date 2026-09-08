# 🔧 RailTwin-X — Remediation Playbook
### Claude Code Execution Plan — Fix Flaws First, Then Upgrade

> Generated from the Global Codebase Audit (Dev Readiness: 54/100 · Prod Readiness: 42/100)
> Target: **0 blockers · 0 criticals · 285/285 tests green · full-stack Docker deployment**

---

## 📖 How To Use This File

1. Open Claude Code in the repo root: `claude`
2. Copy-paste the **PROMPT** block of the current task
3. Review the diff, run the **VERIFY** commands yourself
4. Commit with the suggested message, tick the box in the tracker
5. Move to the next task — **never skip verification**

## ⚖️ Ground Rules (Apply To Every Task)

- **One task = one commit.** Small, revertible, auditable.
- **NEVER modify tests to make them pass.** Fix the code, not the test.
- **Run `python -m pytest -q` after every task.** From Task 0.2 onward: 285 passed, 0 failed is the gate.
- If a fix breaks tests, **revert** (`git checkout -- .`) and report back — don't improvise.
- **Basline:** Before Task 0.2, 8 tests fail (known corruption). After 0.2, everything must be green.
- Do all work on a branch: `git checkout -b fix/audit-remediation`

## ✅ Progress Tracker

| # | ID | Issue | Phase | Est | Done |
|---|----|-------|-------|-----|------|
| 0.1 | SEC-001/002 | Live keys on disk + tracked in git | 🚨 P0 | 15m | ☑ |
| 0.2 | DAT-001 | Corrupted DB, 8 failing tests | 🚨 P0 | 45m | ☑ |
| 0.3 | DEP-001 | Docker omits frontend | 🚨 P0 | 60m | ☑ |
| 1.1 | HAR-001 | localhost QR codes | 🟠 P1 | 15m | ☑ |
| 1.2 | PERF-001 | GET requests write to SQLite | 🟠 P1 | 90m | ☑ |
| 1.3 | SEC-003 | Login brute-force/DoS | 🟠 P1 | 60m | ☑ |
| 1.4 | TIME-001 | Timezone fragmentation | 🟠 P1 | 90m | ☑ |
| 1.5 | ML-001 | GRU docs vs runtime drift | 🟠 P1 | 20m | ☑ |
| 1.6 | GIT-001 | 1.06 GiB history rewrite | 🟠 P1 | 60m | ☐ |
| 2.1 | DEV-001 | Makefile --workers 2 | 🟡 P2 | 5m | ☑ |
| 2.2 | VULN-001 | npm vulnerabilities | 🟡 P2 | 30m | ☑ |
| 2.3 | LIC-001 | No LICENSE | 🟡 P2 | 10m | ☑ |
| 2.4 | SEC-004 | Known seed passwords | 🟡 P2 | 60m | ☑ |
| 2.5 | OBS-001 | No /metrics, print() logging | 🟡 P2 | 90m | ☑ |
| 2.6 | ML-002 | CV Fold 6 collapse | 🟡 P2 | 40m | ☑ |
| 2.7 | MIG-001 | No rollback migrations | 🟡 P2 | 90m | ☑ |
| 2.8 | PRIV-001 | No PII retention (DPDP) | 🟡 P2 | 60m | ☑ |
| 2.9 | ARCH-001 | 1,337-line God router | 🟡 P2 | 180m | ☑ |
| 2.10 | ARCH-002 | Duplicate frontends | 🟡 P2 | 120m | ☑ |
| 3.1 | — | Pin deps + split dev deps | 🔵 P3 | 30m | ☑ |
| 3.2 | — | CI: ruff + mypy | 🔵 P3 | 45m | ☐ |
| 3.3 | — | Async scraper | 🔵 P3 | 45m | ☐ |
| 3.4 | — | Three.js bundle split | 🔵 P3 | 45m | ☐ |
| 3.5 | — | .env.local / Next.js leftover | 🔵 P3 | 15m | ☐ |
| 4.1 | — | NumPy 2.x warnings | ⚪ P4 | 15m | ☐ |
| 4.2 | — | Stale comments | ⚪ P4 | 10m | ☐ |
| 4.3 | — | wmi_test.txt | ⚪ P4 | 2m | ☐ |
| 🏁 | — | Final verification + re-score | — | 30m | ☐ |

---

# 🚨 PHASE 0 — P0 BLOCKERS

## Task 0.1 — SEC-001 + SEC-002: Kill The Leaked Credentials

**👤 MANUAL FIRST (you, in Google Cloud Console — Claude can't do this):**
1. Rotate/revoke the Firebase service-account key from `firebase-admin.json`
2. Rotate the Firebase web API key (`AIzaSy...`)
3. Delete `web/.env` local copy after rotation, recreate with new values

**🤖 PROMPT:**

```text
ROLE: You are remediating security findings SEC-001 and SEC-002.

CONTEXT:
- firebase-admin.json at repo root contains a LIVE GCP service-account private key (P0).
- web/.env is tracked by git (verify: `git ls-files web/.env`) with live Firebase API keys (P0).
- The same API key is hardcoded in _archive/dead-code/web/src/lib/firebase.ts (~line 11).

TASKS:
1. Confirm tracking: `git ls-files | grep -E "web/.env$|firebase-admin.json"`
2. Delete firebase-admin.json from disk (verify it is already in .gitignore; add if missing).
3. Untrack web/.env but KEEP the local file: `git rm --cached web/.env`
4. Ensure .gitignore covers: web/.env, firebase-admin.json — but NOT .env.example files.
5. In _archive/dead-code/web/src/lib/firebase.ts: replace the real API key literal with
   "REDACTED_PLACEHOLDER". Do not delete the file.
6. Scan the entire working tree for the leaked key literal from web/.env and any
   "BEGIN PRIVATE KEY" occurrences (exclude node_modules, .venv). Redact every hit in
   TRACKED files. Report every file you touch.
7. Verify web/.env.example exists with placeholder values only. If missing, create it
   from web/.env's structure with placeholders.

CONSTRAINTS:
- Never commit any file containing real credentials.
- Do not delete web/.env from disk (developer needs it locally until rotation completes).
- Do not run git-filter-repo here — history scrub happens in Task 1.6.

VERIFY (all must pass):
- `git ls-files | grep -E "web/.env$|firebase-admin.json"` → empty output
- `ls firebase-admin.json` → not found
- `grep -rn "AIzaSy" --include="*.ts" --include="*.js" --include="*.json" .` → no real keys
- `python -m pytest -q` → no NEW failures vs. before this task

COMMIT: security: remove tracked credentials and redact leaked keys (SEC-001, SEC-002)
```

---

## Task 0.2 — DAT-001: Restore The Database, Get 285/285 Green

**🤖 PROMPT:**

```text
ROLE: Fix DAT-001 — corrupted route_stations in data/railtwin.db causing 8 test failures.

CONTEXT: data/expand_pan_india_routes.py was previously run against the live DB. It did
`DELETE FROM route_stations` and reassigned corridor trains (12034, 12301, 2421) to wrong
national trunk routes via a `sum(ord(c)) % 14` hash fallback. The pristine DB exists at
data/railtwin.db.gz. data/db.py only auto-extracts the .gz when railtwin.db is absent.

TASKS:
1. Backup the corrupt DB: `cp data/railtwin.db data/railtwin.db.corrupt.bak`
2. Restore pristine DB: remove data/railtwin.db plus any -wal/-shm files, then trigger
   the extraction path in data/db.py (or gunzip data/railtwin.db.gz → data/railtwin.db).
3. Verify canonical corridor: route_stations for train 12034 ORDER BY seq must be exactly
   NDLS, GZB, ALJN, TDL, ETW, CNB, ON, LKO. Train 12301 must start at NDLS. Verify via
   sqlite3 query, not by editing rows.
4. Harden data/expand_pan_india_routes.py so this can NEVER recur:
   a. Remove the wholesale `DELETE FROM route_stations` — script may only INSERT missing
      trains, never delete existing ones.
   b. Remove the modulo-hash fallback entirely. If a train's route can't be matched
      explicitly, SKIP it and log a warning. Never guess.
   c. Add "KANPUR"/"CNB" to keyword matching so corridor trains match correctly.
   d. Add a --dry-run flag (DEFAULT ON) that prints planned changes without writing;
      require explicit --apply to write.
   e. Safety guard: refuse to touch route rows for known corridor train numbers
      (12034, 12301, 2421 and any train whose route contains NDLS..CNB..LKO).
5. Run the full test suite.

CONSTRAINTS:
- Do NOT modify any test file.
- No ad-hoc SQL row edits — restore comes from the .gz archive only.

VERIFY:
- `python -m pytest -q` → 285 passed, 0 failed
- ETA endpoint for train 12034 @ NDLS returns 200 (use FastAPI TestClient in a quick check)
- expand script in default (dry-run) mode performs zero writes

COMMIT: fix(data): restore pristine route DB and harden pan-india route expander (DAT-001)
```

---

## Task 0.3 — DEP-001: Full-Stack Docker Deployment

**🤖 PROMPT:**

```text
ROLE: Fix DEP-001 — Docker deployment omits the web frontend entirely.

TASKS:
1. Rewrite Dockerfile as multi-stage:
   - Stage 1 "frontend-build": FROM node:20-alpine; WORKDIR /build; COPY
     web/package.json + web/package-lock.json; RUN npm ci; COPY web/; RUN npm run build.
   - Stage 2 "backend": FROM python:3.11-slim; install requirements.txt; COPY the
     backend package dirs (api/, engine/, ml/, safety/, notifications/, collector/,
     data/, config.py); COPY --from=frontend-build /build/dist → /app/web/dist.
   - CMD: uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
     (single worker — process-local state architecture).
2. In api/main.py, AFTER all API routers are mounted, add:
   app.mount("/", StaticFiles(directory=<resolved web/dist path>, html=True))
   Mount LAST so /api, /v1, /docs, /openapi.json keep precedence. If web/dist does not
   exist (local dev), skip the mount with a log line — never crash.
3. Update docker-compose.yml: root build context, port 8000, env_file, and a healthcheck
   hitting the real health endpoint path (read api/main.py to find it).
4. Update .dockerignore: exclude web/node_modules, .venv, _archive, tests, root PNGs,
   data/railtwin.db (keep data/railtwin.db.gz).
5. Confirm SPA deep links work (unknown paths serve index.html via html=True) — if not,
   add a catch-all route returning FileResponse of index.html, excluding /api,/v1,/docs.

CONSTRAINTS:
- Do NOT change any API route path or behavior.
- Keep --workers 1 (matches Dockerfile and documented architecture).
- Use npm ci, not npm install, for reproducible builds.

VERIFY:
- `docker build -t railtwin-x .` succeeds
- `docker compose up -d` then:
  - `curl -s http://localhost:8000/` → HTML (SPA index)
  - `curl -s http://localhost:8000/docs` → OpenAPI docs
  - `curl -s "http://localhost:8000/v1/trains/12034/eta?station=NDLS"` → JSON 200
- `python -m pytest -q` → 285 passed (StaticFiles mount must not break TestClient tests)

COMMIT: build(docker): multi-stage build serving React frontend + FastAPI (DEP-001)
```

---

# 🟠 PHASE 1 — P1 CRITICAL FIXES

## Task 1.1 — HAR-001: QR Codes Pointing At Passengers' Own Phones

**🤖 PROMPT:**

```text
ROLE: Fix HAR-001 — api/commercial_routes.py (~line 128) hardcodes
"http://localhost:8000/api/commercial/delay-certificate/verify/{qr_token}" in QR codes.
Passengers scanning the QR hit their own phone's loopback → dead link.

TASKS:
1. Read config.py: confirm settings.PUBLIC_URL exists, check its default + validation.
2. Replace the hardcoded URL with:
   f"{settings.PUBLIC_URL.rstrip('/')}/api/commercial/delay-certificate/verify/{qr_token}"
3. Add production validation in config.py strict mode: when ENV=production, PUBLIC_URL
   must be a valid http(s) URL and must NOT contain localhost or 127.0.0.1.
4. Grep api/, engine/, notifications/ for other hardcoded "localhost:8000"/"127.0.0.1:8000"
   in USER-FACING outputs (QR, SMS, WhatsApp, email bodies) — fix the same way.
   web/vite.config.ts dev proxy is legitimate — leave it.
5. Add/extend a test asserting generated certificate verify URLs start with
   settings.PUBLIC_URL.

VERIFY:
- `grep -rn "localhost:8000" api/ engine/ notifications/` → zero hits in response-generating code
- `python -m pytest -q` → 285 passed

COMMIT: fix(api): use PUBLIC_URL for delay certificate QR links (HAR-001)
```

---

## Task 1.2 — PERF-001: GET Requests Must Not Write To SQLite

**🤖 PROMPT:**

```text
ROLE: Fix PERF-001 — GET /v1/trains/{train_no}/eta and /journey trigger synchronous
SQLite BEGIN IMMEDIATE writes via ledger.record_prediction_receipt(...) per stop.
A single 8-stop journey GET = 8 disk transactions → lock contention + violates GET semantics.

TASKS:
1. Read api/predictor.py (~600–670) and engine/prediction_ledger.py. Map EVERY call path
   to record_prediction_receipt.
2. Implement an async buffered ledger writer inside engine/prediction_ledger.py:
   - record_prediction_receipt(...) becomes non-blocking: appends to an in-memory
     collections.deque guarded by a threading.Lock, returns immediately.
   - A daemon background thread flushes the queue to SQLite in ONE batched transaction
     every N seconds (default 5) OR when queue > M entries (default 100), whichever first.
   - Hash-chain ordering must be preserved: assign the chain hash at ENQUEUE time or
     flush in strict FIFO order. PredictionLedger().verify_chain_integrity() must still
     pass after flushes.
   - Hard cap the queue (e.g., 10,000): drop-oldest with a WARNING log to protect memory.
   - Provide flush_now() and register a graceful shutdown hook (FastAPI lifespan
     shutdown + atexit) so no receipts are lost on exit.
3. GET handlers must no longer perform synchronous writes. Do NOT remove receipt
   recording entirely — the audit trail must survive.
4. Add a concurrency test: hit the ETA endpoint ~50 times concurrently (threads +
   TestClient), assert zero "database is locked" errors, call flush_now(), then assert
   verify_chain_integrity() is valid.

CONSTRAINTS:
- Single-worker process is documented architecture — an in-memory buffer is acceptable.
- Do NOT change the ledger schema or hash format.

VERIFY:
- `python -m pytest -q` → all green incl. existing ledger tests + new concurrency test
- Code inspection: no BEGIN IMMEDIATE on the GET request path

COMMIT: perf(ledger): async buffered receipt writer removes GET-path SQLite writes (PERF-001)
```

---

## Task 1.3 — SEC-003: Login Brute-Force & Argon2id DoS

**🤖 PROMPT:**

```text
ROLE: Fix SEC-003 — /api/auth/login has no brute-force protection. Argon2id
(memory_cost=65536, time_cost=3) means 20 concurrent attempts consume ~1.3 GB RAM and
peg CPU → trivial DoS. Global rate limit (1200 rpm) does not protect this endpoint.

TASKS:
1. Read api/auth_routes.py (login handler, ~54–75) and api/middleware.py
   (existing TokenBucketRateLimiter) — reuse patterns/conventions.
2. Add an auth-specific rate limiter:
   - Per-IP: max 5 login attempts per minute → 429 with Retry-After header.
   - Per-username: max 5 FAILED attempts per 15 min → lockout 15 min (429).
   - In-memory dict with TTL cleanup (process-local is fine — single worker).
3. Anti-enumeration: invalid-username and wrong-password responses must be byte-identical
   (same status code, same message, same timing shape as feasible).
4. Log failed attempts (username, IP, timestamp) at WARNING via the logging module.
   NEVER log passwords or tokens.
5. Tests: (a) 6th rapid attempt same IP → 429; (b) 6th failure same username → 429
   lockout; (c) successful login unaffected within limits; (d) unknown-user vs
   wrong-password responses identical.

CONSTRAINTS:
- Do NOT weaken Argon2 parameters.
- Lockouts must be TTL-based only — never permanent.

VERIFY: `python -m pytest -q` → all green incl. new auth rate-limit tests.

COMMIT: security(auth): login brute-force protection and lockout (SEC-003)
```

---

## Task 1.4 — TIME-001: One Clock To Rule Them All (IST)

**🤖 PROMPT:**

```text
ROLE: Fix TIME-001 — timestamps fragmented across UTC, IST (+05:30), and naive local
time. SQLite compares ISO strings lexicographically, so a UTC stamp sorts 5.5h "older"
than an IST stamp for the same instant → corrupted point-in-time queries.
schema.sql mandates: all timestamps ISO strings in IST (+05:30).

KNOWN OFFENDERS (audit): api/workforce_routes.py:46, api/timetable_routes.py:106,
data/db.py:93, notifications/health.py:18 — plus any others you find.

TASKS:
1. Read engine/clocks.py — confirm get_clock().now_iso() emits IST (+05:30) ISO-8601.
2. Grep the whole tree for writers: `datetime.now(timezone.utc).isoformat()`,
   `datetime.now().isoformat()`, `datetime.utcnow()`, `datetime.now()` in
   api/, data/, engine/, notifications/, collector/ — anywhere a timestamp is
   PERSISTED or returned by the API.
3. Replace every writer with the canonical IST helper. If a circular import blocks
   importing engine.clocks, import inside the function.
4. Write scripts/fix_timestamps.py — a one-off data repair:
   - Scans all tables with ISO string timestamp columns.
   - Detects per-row format (offset +00:00 / naive / +05:30) and converts to IST.
   - DRY-RUN by default: prints per-table counts of rows to convert. Require --apply.
   - Show me the dry-run report BEFORE applying.
5. Add a regression test: on a freshly-seeded DB, every value in every timestamp column
   matches ^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+05:30$.
6. Add a guard test that greps source for `datetime.now(` / `datetime.utcnow(` outside
   engine/clocks.py and tests/ — fail the test on violations.

CONSTRAINTS:
- Do NOT change schema.sql column types.
- Data conversion is destructive — dry-run review is mandatory before --apply.

VERIFY:
- `python -m pytest -q` → all green incl. format regression + grep guard tests
- `grep -rn "datetime.now(" api/ data/ notifications/` → zero hits in writer paths

COMMIT: fix(time): canonical IST clock everywhere + timestamp normalization (TIME-001)
```

---

## Task 1.5 — ML-001: Make Docs Tell The Truth About The GRU

**🤖 PROMPT:**

```text
ROLE: Fix ML-001 — README and docs advertise a served "PyTorch Non-Crossing GRU +
LightGBM Quantile Ensemble", but api/predictor.py (~74–75, 198–205) hardcodes
_gru_sequence_ready = False; runtime serves only LightGBM/NNLS. This is contract drift.

TASKS:
1. Verify runtime truth in api/predictor.py: GRU disabled, served champion is the
   LightGBM direct/delta + NNLS convex ensemble with conformal calibration.
2. Update README.md, docs/HEARTBEAT.md, and any architecture docs:
   - "Served champion: LightGBM Quantile + NNLS convex ensemble, Mondrian conformal
     calibration."
   - "PyTorch Non-Crossing GRU: experimental challenger — NOT served (sequence input
     wiring pending)."
3. If a model-status/health endpoint exists, ensure the served model name is explicit
   in its response.
4. Create docs/ROADMAP.md section: what "GRU sequence inputs wired to real history"
   requires (rolling multi-station history tensors, preprocessing parity, evaluation).
   Do NOT attempt to implement it now.
5. This task changes DOCS ONLY (+ optional health field). Zero predictor behavior change.

VERIFY:
- `grep -rni "GRU" README.md docs/` → every claim now says challenger/experimental
- `python -m pytest -q` → all green (proves no behavior change)

COMMIT: docs(ml): align served-model claims with runtime reality (ML-001)
```

---

## Task 1.6 — GIT-001: The Big History Cleanup
### ⚠️ DESTRUCTIVE — Run ONLY After All Phase 0/1 Tasks Are Committed & Pushed

**👤 MANUAL PREP (you):**
```bash
git clone --mirror <remote-url> ../railtwin-backup.git   # full backup
git status                                              # must be clean
```
Also warn all collaborators: after this, everyone must **re-clone**.

**🤖 PROMPT:**

```text
ROLE: Execute GIT-001 — history rewrite to (a) purge leaked secrets from ALL history
(completing SEC-002) and (b) remove 1+ GiB of committed binaries.

⚠️ This rewrites all history. A mirror backup exists at ../railtwin-backup.git (confirm
with me before proceeding if not).

TASKS:
1. pip install git-filter-repo
2. Analyze bloat: git filter-repo --analyze, then read
   .git/filter-repo/analysis/path-all-sizes.txt — report the top 15 largest paths.
3. Rewrite history removing from ALL commits:
   - firebase-admin.json
   - web/.env (all real .env files with secrets)
   - Root PNG screenshots (Codex Image*.png and similar)
   - data/curated_real_events.csv, data/railtwin.db.gz, large raw GeoJSONs
   - wmi_test.txt
4. Housekeeping: git reflog expire --expire=now --all && git gc --prune=now --aggressive
5. Add a .gitattributes for Git LFS covering data/*.gz, data/*.csv, *.geojson (or
   document the alternative: assets via GitHub Releases).
6. Create scripts/fetch_assets.sh that downloads the removed data files from the
   release/storage location into data/ for dev setup. Update README setup section:
   bold warning that all clones made BEFORE this rewrite are stale and must be re-cloned.
7. Force push: git push --force --all && git push --force --tags

VERIFY:
- `git count-objects -vH` → repo well under 100 MiB (target ~<50 MiB)
- `git log --all --full-history -- firebase-admin.json` → empty
- `git log --all --full-history -- web/.env` → empty
- Fresh clone → scripts/fetch_assets.sh → `python -m pytest -q` → 285 passed

NOTE: This is a history rewrite — no normal commit. Tag the pre-rewrite backup only.
```

---

# 🟡 PHASE 2 — P2 FIXES & UPGRADES

## Task 2.1 — DEV-001: Workers Mismatch (5-Minute Win)

**🤖 PROMPT:**

```text
ROLE: Fix DEV-001 — Makefile (~line 103) runs uvicorn --workers 2, but the architecture
(rate limiter, idempotency cache, SSE counters, simulated clock, kinematic tracker,
SQLite single-writer) is strictly process-local. Two workers = split-brain state.

TASKS:
1. Makefile: change --workers 2 → --workers 1.
2. Grep Makefile, scripts/, docs/, docker-compose.yml for any other multi-worker
   invocations of uvicorn/gunicorn and align them all to 1.
3. Add a comment in Makefile explaining WHY single-worker is a hard constraint.

VERIFY: `grep -rn "workers" Makefile docker-compose.yml scripts/` → all say 1
`python -m pytest -q` → green

COMMIT: fix(make): single uvicorn worker to match process-local architecture (DEV-001)
```

---

## Task 2.2 — VULN-001: Patch Frontend Vulnerabilities

**🤖 PROMPT:**

```text
ROLE: Fix VULN-001 — npm audit reports in web/:
1. ECharts < 6.1.0 XSS (GHSA-fgmj-fm8m-jvvx)
2. React Router open redirect via backslash (GHSA-wrjc-x8rr-h8h6)
3. React Router constructor injection in hydration (GHSA-337j-9hxr-rhxg)

TASKS:
1. `npm --prefix web audit fix` first.
2. If unresolved: manually upgrade react-router-dom and echarts to patched releases.
   Check web/src for breaking API usage (echarts major bump may change APIs) — fix
   usage minimally; do not rewrite chart components.
3. Repeat `npm --prefix livewall audit` — patch livewall the same way if affected.
4. Run builds: `npm --prefix web run build` and `npm --prefix livewall run build`.
5. Run `npm --prefix web run lint`.

VERIFY:
- `npm --prefix web audit` → 0 vulnerabilities
- `npm --prefix livewall audit` → 0 vulnerabilities
- Both builds + lint pass; `python -m pytest -q` green (backend untouched)

COMMIT: security(deps): patch frontend XSS/open-redirect vulnerabilities (VULN-001)
```

---

## Task 2.3 — LIC-001: Add A License

**🤖 PROMPT:**

```text
ROLE: Fix LIC-001 — no LICENSE file, no license fields in any package.json. Default
copyright law applies → legal ambiguity for evaluators.

TASKS:
1. ASK ME which license first (MIT / Apache-2.0 / proprietary). Default to MIT if I
   don't specify — this is a hackathon repo.
2. Create LICENSE at repo root with the correct full text and year/holder.
3. Add "license" field to: root package.json, web/package.json, livewall/package.json.

VERIFY: `ls LICENSE` exists; all three package.json contain a "license" field.
pytest green.

COMMIT: chore(legal): add license and manifest declarations (LIC-001)
```

---

## Task 2.4 — SEC-004: Force Password Change For Seeded Accounts

**🤖 PROMPT:**

```text
ROLE: Fix SEC-004 — data/seed_users.py ships well-known passwords ("RailTwinAdmin2026!",
etc.) for 9 roles, and the distributed DB was seeded with them. Anyone with the repo can
log in as admin on an un-reset install.

TASKS:
1. Write migration 017_add_must_change_password.sql (follow existing migration style in
   scripts/migrations/): ALTER TABLE users ADD COLUMN must_change_password INTEGER
   NOT NULL DEFAULT 0. Register it with the existing migration runner in data/db.py.
2. data/seed_users.py: when seeding with KNOWN demo passwords, set
   must_change_password = 1. (Existing random-password production path already safe —
   verify and keep.)
3. Add POST /api/auth/change-password: verifies old password (Argon2 verify), enforces
   a minimal password policy (length ≥ 10, not equal to old, not in the known-password
   blacklist), hashes with the same Argon2 params, clears the flag. Auth required.
4. Login response and/or /api/auth/me must expose must_change_password.
5. Enforcement: while must_change_password=1, block all non-auth endpoints for that user
   (403 with a clear message) via middleware or dependency. Frontend note: the web app
   should redirect to a change-password screen — add a TODO comment in the auth flow,
   backend enforcement is the hard gate.
6. Tests: (a) flagged user hitting a protected endpoint → 403; (b) change-password with
   wrong old password → 401; (c) successful change clears flag and restores access;
   (d) known-password blacklist rejected.

VERIFY: `python -m pytest -q` → all green incl. new tests; migration applies cleanly on
a fresh DB and on the restored DB.

COMMIT: security(auth): forced password change for seeded accounts (SEC-004)
```

---

## Task 2.5 — OBS-001: Prometheus Metrics + Structured Logging

**🤖 PROMPT:**

```text
ROLE: Fix OBS-001 — no /metrics endpoint, no APM, and print() everywhere. A 3 AM
production failure is currently undebuggable.

TASKS:
1. Add prometheus-fastapi-instrumentator to requirements.txt. In api/main.py, instrument
   the app and expose GET /metrics (unauthenticated is acceptable for now IF it is
   documented; prefer exempting it from auth — check how auth middleware applies and
   exclude /metrics and /health explicitly).
2. Replace print() with Python's logging across api/, engine/, notifications/,
   collector/, data/:
   - Configure in api/main.py: root logger, INFO level, JSON formatter
     (timestamp, level, logger, message, plus request_id when available).
   - Mechanical sweep: print( → logger.info/warning/error based on message content
     (warnings/notices → warning; errors/exceptions → error with exc_info where
     applicable; everything else → info). Preserve message content exactly.
   - Reuse the existing RequestContext middleware's request/correlation ID if present —
     inject it into the log record via a logging.Filter.
   - NEVER log passwords, tokens, keys, or PNRs — if a print currently does, REDACT it.
3. Add a log when SSE client counts change and when SQLite lock waits occur (if
   detectable) — minimum viable ops signals.
4. Add uvicorn log config so access logs go through the same formatter.

CONSTRAINTS:
- No behavior changes — logging only. Do not "fix" things you see along the way; note
  them in the final report instead.
- stdout print() in scripts/ and data/seed* one-off tools may stay if they are
  CLI-only — report which ones you left and why.

VERIFY:
- `curl http://localhost:8000/metrics` → Prometheus text format with request histograms
- `python -m pytest -q` → green (tests may capture stdout — update only CAPTURE
  mechanisms, never assertions, if tests relied on print output; report any such change)
- `grep -rn "print(" api/ engine/ notifications/` → zero (or justified CLI-only remainder)

COMMIT: feat(obs): prometheus metrics + structured JSON logging (OBS-001)
```

---

## Task 2.6 — ML-002: Fix The Fold 6 Collapse

**🤖 PROMPT:**

```text
ROLE: Fix ML-002 — ml/artifacts/metrics.json Fold 6 has only 208 samples (vs 8,400+ in
folds 1–5), MAE explodes to 74.85 min, 80% coverage collapses to 2.4%, dragging CV mean
MAE from 10.63 to 21.66 (std 23.79). Tail-period sparsity poisons aggregate metrics.

TASKS:
1. Read ml/evaluate.py — find fold construction and aggregation.
2. Add a MIN_TEST_SAMPLES guard (default 1000, from config):
   - Folds below threshold are EXCLUDED from aggregate mean/std and flagged
     "excluded_low_samples" in metrics.json with their raw numbers preserved.
   - Also detect truncated tail windows (test period shorter than the standard fold
     span) and exclude them.
3. Regenerate ml/artifacts/metrics.json by re-running evaluation if the data and
   pipeline allow it; otherwise patch the aggregation logic and regenerate the aggregates
   from existing per-fold numbers, preserving raw fold data.
4. tests/test_doc_metric_consistency.py exists and checks doc/metric agreement — the
   docs (HEARTBEAT.md etc.) must be updated to the corrected numbers. NEVER edit the
   test to make it pass; update the real numbers.
5. Report the corrected CV mean/std and what changed.

VERIFY: `python -m pytest -q` green, including test_doc_metric_consistency.py;
metrics.json shows excluded fold with reason.

COMMIT: fix(ml): fold minimum-sample guard for honest CV metrics (ML-002)
```

---

## Task 2.7 — MIG-001: Reversible Migrations

**🤖 PROMPT:**

```text
ROLE: Fix MIG-001 — 16 forward migrations exist (scripts/migrations/001–016, runner in
data/db.py ~115–164) with ZERO rollback capability. A bad migration in staging cannot
be undone without an external backup.

TASKS (choose the LEAST invasive path that satisfies verification):
- Option A (preferred): paired downgrade scripts — for each existing migration NNN_*.sql
  add NNN_*.down.sql that reverses it (drop table/column/index created by the up).
  Extend the runner with `--downgrade N` / `--downgrade-to N` support and record
  downgrades in schema_migrations.
- Option B: adopt yoyo-migrations with up+down per migration — only if Option A is
  genuinely worse here; then migrate the existing 16 SQL files and preserve applied-state.

FOR EVERY PATH:
1. Fresh-DB test: build the schema from scratch via migrations only (delete DB, run
   runner) → pytest green.
2. Round-trip test: fresh DB → up to head → downgrade 2 steps → re-upgrade to head →
   pytest green, integrity_check passes.
3. Down scripts must ONLY reverse what their up created — read each up migration and
   mirror it exactly. Never write a down that drops shared/seeded data tables.
4. Add a test that every NNN_*.sql has a matching down file (or yoyo pair).

CONSTRAINTS: Do not change any existing up migration's semantics.

VERIFY: `python -m pytest -q` green incl. new migration round-trip tests.

COMMIT: feat(db): reversible migrations with paired downgrades (MIG-001)
```

---

## Task 2.8 — PRIV-001: PII Retention (DPDP Act 2023)

**🤖 PROMPT:**

```text
ROLE: Fix PRIV-001 — delay_certificates stores issued_to_name and pnr_no indefinitely;
no retention policy anywhere. India's DPDP Act 2023 requires purpose-limited retention.

TASKS:
1. Add config setting PII_RETENTION_DAYS (default 90).
2. Create scripts/purge_expired_pii.py:
   - DRY-RUN default: reports rows older than retention (delay_certificates, and check
     notification_log / passenger PII columns elsewhere — grep schema).
   - --apply: for delay_certificates older than cutoff → replace issued_to_name with
     "REDACTED" and pnr_no with its SHA-256 hash prefix (preserves verification
     capability without exposing PII). Delete or redact notification_log rows past
     retention.
   - Idempotent (running twice = same result). Emits counts via logging.
3. Wire a scheduled path: add a Makefile target `make purge-pii` and document a cron
   example in the ops runbook. (No in-process scheduler needed — single worker.)
4. Add tests with backdated rows: dry-run counts correct; apply redacts exactly the
   expired rows; fresh rows untouched; idempotency verified.

VERIFY: `python -m pytest -q` green incl. new purge tests.

COMMIT: feat(privacy): PII retention purge job for DPDP compliance (PRIV-001)
```

---

## Task 2.9 — ARCH-001: Break Up The 1,337-Line God Router

**🤖 PROMPT:**

```text
ROLE: Fix ARCH-001 — api/routes.py is 1,337 lines mixing routing, raw SQL, ML feature
transforms, date parsing, and response formatting. High merge-collision risk, hard to test.

⚠️ REFACTOR — behavior must be BIT-IDENTICAL. The route table must not change by one path.

TASKS:
1. FIRST: write a route-snapshot test that asserts the complete sorted list of
   (path, method) pairs served by the app. Run it — this is our safety net. Commit it
   separately first: `test(app): route table snapshot for refactor safety`.
2. Create api/routers/ and split api/routes.py into domain routers by endpoint grouping
   (inspect the file and propose the split; expect roughly: trains.py, eta.py,
   journey.py, corridor.py, gantt.py, sections.py, misc leftovers).
3. Extract data access: raw SQL inside handlers moves to small service/data-access
   functions (api/services/ or data-access modules) with clear names. Keep SQL text
   EXACTLY as-is — no query "improvements" in this task.
4. Move one domain at a time. After EACH extraction: run the route-snapshot test AND
   `python -m pytest -q`. Both green before proceeding to the next.
5. Keep the old import surface working: api/main.py imports updated; if other modules
   import symbols from api/routes.py, re-export from the new modules to avoid breakage.
6. End state: api/routes.py either deleted (if fully distributed) or a thin re-export
   shim; no file in api/ exceeds ~400 lines.

CONSTRAINTS:
- Zero route path/method changes. Zero response-shape changes. Zero SQL text changes.
- If any test fails mid-refactor: stop, revert that step, report — do not adjust tests.

VERIFY: route-snapshot test green; `python -m pytest -q` → 285+ green;
`wc -l api/routes.py` → thin or gone; largest new file < 400 lines.

COMMIT (series): refactor(api): extract <domain> router from god-file (ARCH-001)
```

---

## Task 2.10 — ARCH-002: Unify The Frontend Monorepo

**🤖 PROMPT:**

```text
ROLE: Fix ARCH-002 — web/ and livewall/ are two independent Vite/React apps with
duplicated package.json, tsconfig, and duplicated TS interfaces (train positions,
alerts). API contract changes require parallel manual edits.

TASKS:
1. Introduce npm workspaces at the root: package.json with
   "workspaces": ["packages/*", "web", "livewall"].
2. Create packages/shared-types: the duplicated TypeScript interfaces/types extracted
   from BOTH apps (train position, alert, ETA, station types). Name scope
   @railtwin/shared-types. Keep the exact type shapes — only move them.
3. Update web/ and livewall/: import from @railtwin/shared-types; delete their local
   duplicates; adjust tsconfig (paths/bundlers resolve workspace package); remove
   per-app duplicated devDependencies that the root now provides.
4. Update CI (.github/workflows/tests.yml): install at root once, run both app builds.
5. Update Dockerfile Task-0.3 frontend stage: build from workspace root
   (npm ci at root, npm run build --workspace web) so web/dist still lands correctly.
   Verify the container still serves the SPA.
6. Keep both apps independently deployable — this is shared code, not app merging.

CONSTRAINTS:
- Type shapes unchanged — pure relocation.
- Both apps must build; both dev servers must still work.

VERIFY:
- `npm ci` at root; `npm run build --workspace web` and `--workspace livewall` pass
- `npm --prefix web run lint` passes; `python -m pytest -q` green
- Docker build + curl smoke test from Task 0.3 still pass

COMMIT: refactor(web): npm workspace monorepo with shared types (ARCH-002)
```

---

# 🔵 PHASE 3 — P3 UPGRADES

## Task 3.1 — Pin Dependencies + Split Dev Deps

**🤖 PROMPT:**

```text
ROLE: Upgrade — requirements.txt uses loose >= pins (non-reproducible builds) and ships
pytest/hypothesis into the production Docker image.

TASKS:
1. Generate a pinned requirements.txt from the current working environment
   (pip freeze filtered to actually-imported packages; verify each is imported —
   report any freeze entries you drop).
2. Create requirements-dev.txt: pytest, hypothesis, ruff, mypy, pip-audit — including
   versions.
3. Remove pytest/hypothesis from requirements.txt.
4. Dockerfile: install ONLY requirements.txt in the runtime image (dev deps never
   enter the container). CI workflow installs requirements-dev.txt.
5. Update README setup instructions to match (pip install -r requirements-dev.txt
   for development).

VERIFY: `pip install -r requirements.txt` in a fresh venv + `python -m pytest -q` green
after also installing dev deps; Docker build succeeds and image contains no pytest
(`docker run --rm railtwin-x python -c "import pytest"` → ModuleNotFoundError is EXPECTED).

COMMIT: build(deps): pin versions and split dev dependencies (P3)
```

---

## Task 3.2 — CI: Add ruff + mypy

**🤖 PROMPT:**

```text
ROLE: Upgrade — .github/workflows/tests.yml runs pytest and npm lint but ZERO Python
linting or type checking.

TASKS:
1. Add ruff config (ruff.toml or pyproject section): line-length 100; select a sensible
   rule set (E, F, W, I, B, UP); ignore rules that would flood a legacy codebase —
   document each ignore with a comment.
2. Run `ruff check .` locally. Fix ONLY mechanical/safe violations (unused imports,
   sorting). Report — do not auto-fix risky categories.
3. Add mypy config: start permissive (ignore_missing_imports=True) but real for api/,
   engine/, safety/. Run locally; add `# type: ignore` ONLY where a third-party stub is
   missing — never to silence a real type error. Fix genuinely-wrong signatures found.
4. Add CI steps after the existing pytest job: ruff check, ruff format --check
   (add config for format), mypy. Make them BLOCKING.
5. Pre-commit hook file (.pre-commit-config.yaml) with ruff for local dev.

VERIFY: ruff/mypy clean locally; CI YAML valid (actionlint or careful review);
`python -m pytest -q` green.

COMMIT: ci: add ruff and mypy enforcement (P3)
```

---

## Task 3.3 — Async Collector I/O

**🤖 PROMPT:**

```text
ROLE: Upgrade — collector/adapters/scrape.py (~41) uses synchronous requests.Session
plus blocking time.sleep(2.0), stalling the collector thread during multi-train polling.

TASKS:
1. Read how scrape.py is invoked (sync loop? async context? thread?). Choose:
   - If the caller is async → convert to httpx.AsyncClient + asyncio.sleep, with
     jittered delays (2.0 ± 0.5s).
   - If callers are sync and conversion is invasive → keep requests but add explicit
     timeouts (connect 5s / read 15s), retry with exponential backoff + jitter
     (max 3), and run sleeps in small increments. Report which path you chose and why.
2. Never let one train's scrape failure block others (per-target try/except, errors
   logged at WARNING with train id).
3. Response validation: malformed HTML/JSON from external sources must not raise into
   the polling loop — catch, log, skip cycle.

CONSTRAINTS: No change to polling cadence semantics or the data written.

VERIFY: `python -m pytest -q` green; manual run of the collector for one cycle logs
normally; no blocking calls inside any async function (grep asyncio + time.sleep
co-location).

COMMIT: perf(collector): non-blocking HTTP with backoff (P3)
```

---

## Task 3.4 — Frontend Bundle Diet

**🤖 PROMPT:**

```text
ROLE: Upgrade — web build emits a 907 kB vendor-three chunk (threshold ~500 kB), making
first paint slow.

TASKS:
1. In web/vite.config.ts: add rollupOptions.output.manualChunks separating three,
   echarts, and react vendor groups.
2. Audit web/src routes using Three.js-heavy components: convert them to React.lazy +
   dynamic import so three loads only when a 3D view opens. Add <Suspense> fallbacks
   (loading skeleton or spinner — match existing loading-state patterns).
3. Verify with `npm --prefix web run build` and the emitted chunk-size report: no chunk
   over ~500 kB; three/echarts chunks lazy (loaded on navigation, not initial).
4. Confirm the app still boots to a functional first screen without three loaded.

CONSTRAINTS: No visual/UX changes beyond loading states. No dependency version changes
here (Task 2.2 handled those).

VERIFY: build passes; chunk report shows split + lazy loading; `python -m pytest -q` green.

COMMIT: perf(web): code-split three.js and echarts, lazy 3D routes (P3)
```

---

## Task 3.5 — .env.local & Next.js Leftover Cleanup

**🤖 PROMPT:**

```text
ROLE: Upgrade — web/.env.local is TRACKED in git and declares NEXT_PUBLIC_API_URL inside
a Vite project (Next.js leftover from a rewrite).

TASKS:
1. `git rm --cached web/.env.local` (keep local file); add web/.env.local to .gitignore.
2. Create/extend web/.env.example with VITE_API_URL (correct Vite convention) and any
   other vars web/src actually reads (grep import.meta.env across web/src).
3. Grep web/src for `process.env.NEXT_PUBLIC` — if any code still reads it, fix the
   reads to import.meta.env.VITE_* (verify each var is provided via the API layer).
4. Remove other Next.js references in web config/comments where they mislead.

VERIFY: `git ls-files | grep env.local` → empty; `grep -rn "NEXT_PUBLIC" web/src` → zero;
`npm --prefix web run build` + lint pass; pytest green.

COMMIT: chore(web): remove Next.js env leftovers, untrack .env.local (P3)
```

---

# ⚪ PHASE 4 — P4 POLISH

## Task 4.1 — NumPy 2.x Warnings

**🤖 PROMPT:**

```text
ROLE: Polish — pytest emits 122 NumPy 2.x deprecation warnings from
joblib.numpy_pickle (array shape set directly).

TASKS:
1. Determine the clean fix: upgrade joblib/lightgbm/scikit-learn to NumPy-2-compatible
   versions OR pin numpy to a 1.x series consistent with the ML stack — pick whichever
   keeps versions in requirements.txt honest and the stack reproducible. Report your
   choice and reasoning.
2. Update requirements.txt accordingly and reinstall.
3. Run pytest with -W error::DeprecationWarning scoped to the numpy/joblib origin —
   goal: zero numpy_pickle warnings in a normal run.

VERIFY: `python -m pytest -q 2>&1 | grep -ci "numpy_pickle\|DeprecationWarning.*numpy"` → 0;
suite green; models still load and predictions served (a quick inference smoke test).

COMMIT: chore(deps): resolve numpy 2.x pickle deprecation warnings (P4)
```

## Task 4.2 — Stale Comments

**🤖 PROMPT:**

```text
ROLE: Polish — api/main.py (~200) comments mention "Next.js dashboard integration" but
the frontend is Vite+React. Misleading archaeology.

TASKS: grep the whole repo (excluding _archive, node_modules) for "Next.js"/"nextjs"
references in comments and docs; update to reflect the Vite+React reality. Comments
ONLY — zero code changes.

VERIFY: `grep -rni "next\.js" --include="*.py" --include="*.md" . | grep -v _archive` → 0
misleading hits; pytest green.

COMMIT: docs(comments): remove stale Next.js references (P4)
```

## Task 4.3 — wmi_test.txt

**🤖 PROMPT:**

```text
ROLE: Polish — stray 8-byte wmi_test.txt at root.

TASKS: `git rm wmi_test.txt`; confirm no code references it (grep first); done.

VERIFY: file gone from git ls-files and disk; pytest green.

COMMIT: chore: remove stray wmi_test.txt (P4)
```

---

# 🏁 FINAL VERIFICATION — The Victory Lap

**🤖 PROMPT:**

```text
ROLE: Final gate — prove all remediation landed. Run and report EVERY result:

1. `python -m pytest -q` → expect 285+ passed, 0 failed
2. `npm --prefix web run build && npm --prefix web run lint` → pass
3. `npm --prefix livewall run build` → pass
4. `npm --prefix web audit` and `npm --prefix livewall audit` → 0 vulnerabilities
5. `python -m pip_audit` → 0 known CVEs (or justified exceptions)
6. `ruff check .` → clean; `mypy` → clean
7. `docker build -t railtwin-x .` → success
8. `docker compose up -d` + smoke: `/` returns HTML, `/docs` works,
   `/v1/trains/12034/eta?station=NDLS` returns 200 JSON, `/metrics` returns Prometheus text
9. `git ls-files | grep -E "\.env$|firebase-admin|env.local"` → empty
10. `git count-objects -vH` → repo size reported
11. `git log --all --full-history -- firebase-admin.json web/.env` → empty
12. Ledger integrity: run verify_chain_integrity() → valid
13. `PRAGMA integrity_check` + `PRAGMA foreign_key_check` on data/railtwin.db → clean

Then produce a REMEDIATION-REPORT.md: every audit ID (SEC-001…P4s) → status
(FIXED / PARTIAL / DEFERRED with reason), the before/after scores per audit category,
and the two headline numbers:
OVERALL DEVELOPMENT READINESS: X/100 (was 54)
OVERALL PRODUCTION READINESS:  X/100 (was 42)

Be honest — anything not verified is NOT marked fixed.
```

---

## 🧭 After The Victory Lap

1. Merge `fix/audit-remediation` → main, tag `v1.0-remediated`
2. Rotate credentials **if not already done** (Task 0.1 manual steps — non-negotiable)
3. Roadmap items intentionally deferred: GRU sequence wiring (ML-001 roadmap),
   multi-worker readiness, OpenTelemetry tracing, Alembic-style full migration framework
4. Re-run the full audit prompt quarterly — the score should never silently drift down
