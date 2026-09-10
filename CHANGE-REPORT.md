# RailTwin-X — Full Change Report
**Branch:** `fix/audit-remediation`
**Period:** 2026-09-08
**Total:** 338 files changed · **19,775 lines added** · **8,985 lines deleted**
**Commits:** 39 commits across 5 phases (P0 → P4)

---

## Grand Summary

| Metric | Value |
|--------|-------|
| Commits | 39 |
| Files changed | 338 |
| Lines added | +19,775 |
| Lines deleted | −8,985 |
| Net change | +10,790 lines |
| Tests before | 0 passing (suite broken) |
| Dev Readiness | 54 → **85 / 100** *(Internal self-assigned claim)* |
| Prod Readiness | 42 → **78 / 100** *(Internal self-assigned claim)* |

> [!IMPORTANT]
> **DOCS INTEGRITY / AUTHORITATIVE BENCHMARK (WO-22):** The scores above (85/100, 78/100) are internally generated developer estimations. They are NOT certified scores. The ONLY authoritative benchmark score for this repository is the independent external GRANDMASTER AUDIT PROTOCOL v3.1 re-audit score: **60/100 (CRITICAL / CONDITIONAL PASS)**. All claims of 84/100, 85/100, or 78/100 are internal and superseded by v3.1.

---

## Phase 0 — Credential Purge (P0)

### Commit `ead3099` — `security: remove tracked credentials and redact leaked keys (SEC-001, SEC-002)`
**5 files changed · +1,019 lines · −13 lines**

| File | Change | +/− |
|------|--------|-----|
| `REMEDIATION.md` | Created full 1,004-line remediation playbook | +1,004 |
| `web/.env` | **DELETED** — contained live NEXT_PUBLIC_API_URL + secrets | −11 |
| `web/.env.example` | Created safe template with placeholder vars | +13 |
| `_archive/dead-code/web/src/lib/firebase.ts` | Redacted real Firebase config → placeholder strings | +1/−1 |
| `_archive/reports/CLEANUP-REPORT.md` | Updated to reflect secret removal | +1/−1 |

**What changed:** Firebase service-account key and API secrets that were tracked in git were removed from the working tree. An `.env.example` template was created so new developers know which variables to set without seeing real values.

---

## Phase 0 (extra) — Data / Docker / API Hardening

### Commit `caa8b1b` — `fix(data): restore pristine route DB and harden pan-india route expander (DAT-001)`
**3 files changed · +148 lines · −37 lines**

### Commit `12d5c72` — `build(docker): multi-stage build serving React frontend + FastAPI (DEP-001)`
**6 files changed · +130 lines · −87 lines**

| File | Change |
|------|--------|
| `Dockerfile` | Rewrote to multi-stage: Node build stage → Python runtime stage |
| `web/dist/index.html` | Rebuilt from clean Vite output |

### Commit `23a45fb` — `fix(api): use PUBLIC_URL for delay certificate QR links (HAR-001)`
**4 files changed · +64 lines · −2 lines**

### Commit `608af9d` — `perf(ledger): async buffered receipt writer (PERF-001)`
**4 files changed · +197 lines · −29 lines**

| File | Change |
|------|--------|
| `engine/prediction_ledger.py` | Converted synchronous receipt writes to async buffered queue |
| `tests/test_ledger_concurrency.py` | +44 lines of concurrency tests |

---

## Phase 1 — P1 Critical Security & Correctness

### Commit `e0e7994` — `security(auth): login brute-force protection and lockout (SEC-003)`
**4 files changed · +373 lines · −5 lines**

| File | Change | Lines |
|------|--------|-------|
| `api/routers/auth.py` | Added rate-limit middleware, lockout counter, 429 response | +200 |
| `tests/test_auth_rate_limit.py` | **NEW FILE** — 168-line test suite for brute-force protection | +168 |

### Commit `f18be0d` — `fix(time): canonical IST clock everywhere + timestamp normalization (TIME-001)`
**31 files changed · +599 lines · −107 lines**

| Key Files | Change |
|-----------|--------|
| `engine/clock.py` | Created canonical `now_ist()` → `datetime` with `Asia/Kolkata` tzinfo |
| `api/main.py`, all routers | Replaced all `datetime.utcnow()` + naive `datetime.now()` calls with `now_ist()` |
| `collector/`, `safety/`, `engine/` | Propagated IST-aware timestamps through 28 files |
| `tests/test_timestamps.py` | **NEW FILE** — 194-line suite verifying no naive datetimes leak |

### Commit `9b37b3a` — `docs(ml): align served-model claims with runtime reality (ML-001)`
**14 files changed · +89 lines · −18 lines**

| Key Files | Change |
|-----------|--------|
| `docs/spec/PRD.md` | Removed false GRU-sequence wiring claim; noted as roadmap item |
| `docs/architecture.md` | Corrected ML pipeline diagram to match actual served ensemble |
| `ml/README.md` | Updated model card: GBM ensemble is champion, GRU is experimental |

### Commit `b1476a5` — `fix(make): single uvicorn worker (DEV-001)`
**4 files changed · +7 lines · −5 lines**

| File | Change |
|------|--------|
| `Makefile` | `--workers 4` → `--workers 1` |
| `Dockerfile` | CMD updated to single worker |
| `docs/pipelines/README.md` | Noted single-worker architecture constraint |

---

## Phase 2 — P2 High Priority

### Commit `827d9e2` — `fix(security): patch npm audit vulnerabilities (VULN-001)`
**4 files changed · +405 lines · −2,449 lines**

| File | Change |
|------|--------|
| `web/package.json` | Bumped vulnerable transitive deps |
| `web/package-lock.json` | Regenerated — net −2,044 lines (removed vulnerable subtrees) |

### Commit `b601bcd` — `chore(legal): add license and manifest declarations (LIC-001)`
**5 files changed · +25 lines · −1 line**

| File | Change |
|------|--------|
| `LICENSE` | **NEW** — MIT License |
| `MANIFEST.in` | **NEW** — Python package manifest |
| `pyproject.toml` | Added `license = "MIT"` field |

### Commit `529bc08` — `security(auth): forced password change for seeded accounts (SEC-004)`
**7 files changed · +409 lines · −9 lines**

| Key Files | Change |
|-----------|--------|
| `scripts/migrations/017_add_must_change_password.sql` | **NEW** — `must_change_password BOOLEAN DEFAULT 0` column |
| `scripts/migrations/017_add_must_change_password.down.sql` | **NEW** — down-migration |
| `api/routers/auth.py` | Added check: 403 with `must_change_password=true` signal if flag set |
| `api/routers/users.py` | Added `POST /v1/users/change-password` endpoint |
| `tests/test_password_change.py` | **NEW** — 218-line test suite |

### Commit `7909904` — `feat(obs): prometheus metrics + structured JSON logging (OBS-001)`
**12 files changed · +257 lines · −42 lines**

| Key Files | Change |
|-----------|--------|
| `api/main.py` | Added `prometheus_fastapi_instrumentator`, `/metrics` endpoint |
| `api/logging_config.py` | **NEW** — JSON log formatter with `trace_id`, `train_no`, `level` |
| `tests/test_observability.py` | **NEW** — 103-line test suite for `/metrics` + log format |

### Commit `a287139` — `fix(ml): fold minimum-sample guard for honest CV metrics (ML-002)`
**6 files changed · +105 lines · −18 lines**

| Key Files | Change |
|-----------|--------|
| `ml/train.py` | Added `min_samples_per_fold = 30` guard; skip CV if fold too small |
| `ml/eval.py` | Removed leaking future data from validation window |
| `tests/test_eval_protocol.py` | +26 lines asserting fold-size guard fires correctly |

### Commit `61efd17` — `feat(db): reversible migrations with paired downgrades (MIG-001)`
**20 files changed · +395 lines · −9 lines**

| Key Files | Change |
|-----------|--------|
| `scripts/migrations/001_phase0_foundation.down.sql` | **NEW** — +13 lines |
| `scripts/migrations/002_phase1_live_truth.down.sql` | **NEW** — +11 lines |
| *(+ 14 more `.down.sql` files)* | **NEW** — paired rollback for every migration |
| `scripts/migrate.py` | Added `--down` flag executing down-migrations in reverse order |
| `tests/test_migrations.py` | **NEW** — 193-line up+down round-trip test suite |

### Commit `5365a25` — `feat(privacy): pii retention policy and purge job (PRIV-001)`
**6 files changed · +672 lines · −3 lines**

| Key Files | Change |
|-----------|--------|
| `scripts/purge_expired_pii.py` | **NEW** — 276-line scheduled purge script; deletes PII rows older than 90 days per DPDP Act §8(7) |
| `tests/test_privacy_purge.py` | **NEW** — 306-line test suite: retention window, partial purge, audit trail |

### Commit `ef2d273` — `test(app): route table snapshot for refactor safety`
**1 file changed · +932 lines**

| File | Change |
|------|--------|
| `tests/test_route_snapshot.py` | **NEW** — 932-line golden snapshot of every route (method + path + response shape) to ensure refactor doesn't break any endpoint |

### Commits `1eec655` → `fb260eb` — `refactor(api): extract trains/stations/ops/advisory/system_meta routers (ARCH-001)`
**5 commits · 18 files changed · 1,599 lines added · 1,346 lines deleted**

| Files Created | Lines |
|---------------|-------|
| `api/routers/trains.py` | +176 |
| `api/routers/stations.py` | +98 |
| `api/routers/ops.py` | +134 |
| `api/routers/advisory.py` | +121 |
| `api/routers/system_meta.py` | +92 |
| `api/services/train_service.py` | +76 |
| `api/services/station_service.py` | +51 |
| `api/services/ops_service.py` | +64 |
| `api/services/advisory_service.py` | +68 |
| `api/services/meta_service.py` | +39 |

**`api/main.py`:** 1,337 lines → **202 lines** (−1,135 lines — all logic moved to routers + services)

### Commit `a653d90` — `refactor(web): npm workspace monorepo with shared types (ARCH-002)`
**28 files changed · +5,225 lines · −1,623 lines**

| Key Files | Change |
|-----------|--------|
| `packages/shared-types/src/index.ts` | **NEW** — 638-line shared type library (Train, Station, Conflict, ETA…) |
| `packages/shared-types/package.json` | **NEW** |
| `packages/shared-types/tsconfig.json` | **NEW** |
| `package.json` (root) | Added `workspaces: ["web","livewall","packages/*"]` |
| `web/src/lib/types.ts` | Now re-exports from `@railtwin/shared-types` (−548 lines own definitions) |
| `livewall/src/lib/types.ts` | Now re-exports from `@railtwin/shared-types` (−167 lines own definitions) |
| `package-lock.json` | Regenerated for workspace deps (+5,314 lines) |

---

## Phase 3 — P3 Performance & Quality

### Commit `381b4d2` — `build(deps): pin versions and split dev dependencies (P3)`
**4 files changed · +31 lines · −21 lines**

| File | Change |
|------|--------|
| `requirements.txt` | All 19 runtime deps pinned to exact versions (`==`) |
| `dev-requirements.txt` | **NEW** — 12 dev/test deps separated (pytest, mypy, ruff, etc.) |
| `.github/workflows/tests.yml` | Updated to install both files separately |

### Commit `ddb4273` — `ci: add ruff and mypy enforcement (P3)`
**255 files changed · +7,873 lines · −4,314 lines**

| Key Changes | Detail |
|-------------|--------|
| `.github/workflows/tests.yml` | Added `ruff check .` and `mypy api engine safety` steps |
| `.pre-commit-config.yaml` | **NEW** — 8-line pre-commit config (ruff + mypy hooks) |
| `ruff.toml` | **NEW** — project-wide ruff config (E, F, I, UP rules) |
| `mypy.ini` | **NEW** — mypy config (strict=false, ignore\_missing\_imports=true) |
| 250 Python files | Auto-fixed by `ruff format` (import ordering, trailing whitespace, quote style) — net +3,559 lines of reformatted code |

**Result:** `ruff check .` → clean · `mypy api engine safety` → 0 errors in 65 files

### Commit `4ec297c` — `perf(collector): non-blocking HTTP with backoff (P3)`
**3 files changed · +253 lines · −38 lines**

| File | What Changed | Lines |
|------|-------------|-------|
| `collector/adapters/scrape.py` | Full rewrite | +215 / −38 |
| `tests/test_collector.py` | 5 new tests added | +74 |
| `REMEDIATION.md` | Task 3.3 marked ☑ | +1/−1 |

**Key changes in `scrape.py`:**
- Added `logging`, `random`, `time` imports
- `_interruptible_sleep(seconds)` — sleeps in 0.1s slices so the process can be interrupted cleanly
- `ScrapeSource.__init__` — new params: `timeout=(5.0, 15.0)`, `max_retries=3`, `polite_delay=None`
- `_retry_backoff(attempt)` — exponential backoff: `2^attempt + jitter(0–1s)`, capped at 32s
- `_scrape_erail()` and `_scrape_indiarailinfo()` — per-target scrapers with response validation before parse
- `fetch_running_status()` — returns `[]` instead of raising `RuntimeError` on all-failure
- Per-target `try/except` with `WARNING` log including `train_no`

### Commit `57a7096` — `perf(web): code-split three.js and echarts, lazy 3D routes (P3)`
**4 files changed · +54 lines · −14 lines**

| File | What Changed | Lines |
|------|-------------|-------|
| `web/vite.config.ts` | Added `manualChunks` + `three` alias | +36/−5 |
| `web/src/landing/LandingPage.tsx` | `ThreeCorridor` → `React.lazy()` + `<Suspense>` | +14/−3 |
| `web/dist/index.html` | Rebuilt with new chunk references | +4/−6 |

**Bundle result (gzip):**

| Chunk | Size (gzip) |
|-------|-------------|
| `vendor-react` (initial load only) | 212 kB / 69 kB gz |
| `vendor-three` (lazy) | 465 kB / 127 kB gz |
| `vendor-three-shaders` (lazy) | 167 kB / 36 kB gz |
| `vendor-three-fiber` (lazy) | 137 kB / 45 kB gz |
| `vendor-three-drei` (lazy) | 80 kB / 24 kB gz |
| `vendor-three-math` (lazy) | 80 kB / 24 kB gz |

**Before:** one 1.2 MB three.js chunk always in initial load
**After:** initial load is only `vendor-react` (212 kB gzip)

### Commit `8b16777` — `chore(web): remove Next.js env leftovers, untrack .env.local (P3)`
**5 files changed · +7 lines · −4 lines**

| File | What Changed |
|------|-------------|
| `.gitignore` | Added explicit `web/.env.local` line |
| `web/src/lib/api.ts` | Added `const API_BASE = (import.meta.env.VITE_API_URL \|\| '')` — wired into `fetchJson()` |
| `web/.env.local` | Renamed `NEXT_PUBLIC_API_URL` → `VITE_API_URL` (kept locally, now untracked) |
| `web/dist/index.html` | Rebuilt |
| `REMEDIATION.md` | Task 3.5 marked ☑ |

---

## Phase 4 — P4 Polish

### Commit `d723b92` — `chore(deps): resolve numpy 2.x pickle deprecation warnings (P4)`
**1 file changed · +1 line · −1 line**

| File | Change |
|------|--------|
| `requirements.txt` line 4 | `joblib==1.5.3` → `joblib==1.6.0` |

**Why:** joblib 1.6.0 uses `np.reshape()` instead of deprecated `array.shape = self.shape` — eliminates all `numpy_pickle` DeprecationWarnings when loading `.pkl` model files with NumPy 2.x.
**Verified:** `pytest 2>&1 | Select-String numpy_pickle` → **0 matches**

### Commit `052fb7a` — `docs(comments): remove stale Next.js references (P4)`
**3 files changed · +3 lines · −3 lines**

| File | Line | Before | After |
|------|------|--------|-------|
| `api/main.py:296` | comment | `# Configure CORS for Next.js dashboard integration` | `# Configure CORS for Vite/React frontend` |
| `docs/spec/PRD.md:90` | stack list | `· Next.js ·` | `· Vite + React ·` |
| `docs/architecture.md:82` | Mermaid label | `"6. Next.js Controller Dashboard"` | `"6. Vite/React Controller Dashboard"` |

### Task 4.3 — `chore: remove stray wmi_test.txt (P4)`
**No commit needed** — file was never tracked by git (untracked). Deleted from disk with `Remove-Item wmi_test.txt`. Verified: `rg "wmi_test" api/ engine/ collector/ safety/` → **0 results**.

### Commit `30ef2ae` — `chore(deps): pin cryptography==50.0.0 and pypdf==6.16.1 (CVE fix)`
**1 file changed · +2 lines**

| File | Change |
|------|--------|
| `requirements.txt` | Added `cryptography==50.0.0` (fixes PYSEC-2026-3552) |
| `requirements.txt` | Added `pypdf==6.16.1` (fixes CVE-2026-84309, CVE-2026-84310, CVE-2026-84311) |

---

## Test Suite Growth

| Test File | Status | Lines Added |
|-----------|--------|-------------|
| `tests/test_auth_rate_limit.py` | NEW | +168 |
| `tests/test_collector.py` | EXTENDED | +74 (5 new tests) |
| `tests/test_eval_protocol.py` | EXTENDED | +26 |
| `tests/test_migrations.py` | NEW | +193 |
| `tests/test_observability.py` | NEW | +103 |
| `tests/test_password_change.py` | NEW | +218 |
| `tests/test_privacy_purge.py` | NEW | +306 |
| `tests/test_route_snapshot.py` | NEW | +932 |
| `tests/test_timestamps.py` | NEW | +194 |

**Total new test lines: +2,214**
**Final result: 325 passed, 0 failed**

---

## Files Created (New — Did Not Exist Before)

| File | Lines | Purpose |
|------|-------|---------|
| `LICENSE` | 21 | MIT License |
| `MANIFEST.in` | 5 | Python package manifest |
| `REMEDIATION.md` | 1,005 | Full remediation playbook |
| `REMEDIATION-REPORT.md` | 114 | Final audit report |
| `.pre-commit-config.yaml` | 8 | Pre-commit hooks (ruff + mypy) |
| `ruff.toml` | ~30 | Ruff linter config |
| `mypy.ini` | ~20 | Mypy type-checker config |
| `dev-requirements.txt` | 12 | Dev/test dependencies |
| `web/.env.example` | 13 | Safe env template |
| `packages/shared-types/src/index.ts` | 638 | Shared TypeScript types |
| `packages/shared-types/package.json` | 19 | Workspace package manifest |
| `packages/shared-types/tsconfig.json` | 20 | TS config for shared pkg |
| `api/routers/trains.py` | ~176 | Trains router (split from god-file) |
| `api/routers/stations.py` | ~98 | Stations router |
| `api/routers/ops.py` | ~134 | Ops router |
| `api/routers/advisory.py` | ~121 | Advisory router |
| `api/routers/system_meta.py` | ~92 | System/meta router |
| `api/services/train_service.py` | 76 | Business logic layer |
| `api/services/station_service.py` | 51 | Business logic layer |
| `api/services/ops_service.py` | 64 | Business logic layer |
| `api/services/advisory_service.py` | 68 | Business logic layer |
| `api/services/meta_service.py` | 39 | Business logic layer |
| `api/logging_config.py` | ~80 | Structured JSON logger |
| `engine/clock.py` | ~40 | Canonical IST clock |
| `scripts/purge_expired_pii.py` | 276 | DPDP-compliant PII purge |
| `scripts/migrations/*.down.sql` (×16) | ~80 | Down-migrations for every schema change |
| `tests/test_auth_rate_limit.py` | 168 | Brute-force protection tests |
| `tests/test_migrations.py` | 193 | Migration round-trip tests |
| `tests/test_observability.py` | 103 | Prometheus + logging tests |
| `tests/test_password_change.py` | 218 | Password change endpoint tests |
| `tests/test_privacy_purge.py` | 306 | PII purge tests |
| `tests/test_route_snapshot.py` | 932 | Route golden snapshot |
| `tests/test_timestamps.py` | 194 | Timezone-aware datetime tests |

---

## Files Deleted

| File | Reason |
|------|--------|
| `web/.env` | Contained live secrets — removed from git tracking |
| `wmi_test.txt` | Stray 8-byte debug file at repo root |

---

## Key Metrics Per Phase

| Phase | Commits | Files | +Lines | −Lines | Net |
|-------|---------|-------|--------|--------|-----|
| P0 — Credential Purge | 1 | 5 | +1,019 | −13 | +1,006 |
| P0-extra — Data/Docker | 4 | 17 | +539 | −155 | +384 |
| P1 — Critical Security | 5 | 60 | +1,477 | −144 | +1,333 |
| P2 — High Priority | 9 | 111 | +8,419 | −5,201 | +3,218 |
| P3 — Performance | 5 | 263 | +8,199 | −4,369 | +3,830 |
| P4 — Polish | 4 | 5 | +7 | −2 | +5 |
| Docs/Tracker | 11 | 12 | +115 | −15 | +100 |
| **TOTAL** | **39** | **338** | **+19,775** | **−8,985** | **+10,790** |

---

## Final Verification Gate Results

| Check | Command | Result |
|-------|---------|--------|
| Tests | `pytest -q` | ✅ **325 passed, 0 failed** in 3m38s |
| Linter | `ruff check .` | ✅ All checks passed (298 files) |
| Formatter | `ruff format --check .` | ✅ 298 files already formatted |
| Types | `mypy api engine safety` | ✅ 0 errors in 65 files |
| npm audit web | `npm audit --prefix web` | ✅ 0 vulnerabilities |
| npm audit livewall | `npm audit --prefix livewall` | ✅ 0 vulnerabilities |
| pip audit | `python -m pip_audit` | ✅ No known vulnerabilities |
| Web build | `npm --prefix web run build` | ✅ Built in 5.57s |
| Livewall build | `npm --prefix livewall run build` | ✅ Built in 577ms |
| Secrets in index | `git ls-files \| grep .env` | ✅ Empty |
| Ledger integrity | `verify_chain_integrity()` | ✅ valid=True, 15,710 blocks |
| DB integrity | `PRAGMA integrity_check` | ✅ ok |
| Docker | N/A | ⚠️ Not run (Docker unavailable) |

---

## 3 Items Still Open

| Item | Status | Action Required |
|------|--------|----------------|
| GIT-001 — secrets in old git history | DEFERRED by user | `git filter-repo --path firebase-admin.json --invert-paths` + force-push |
| Docker smoke test | NOT VERIFIED | Run `docker build -t railtwin-x .` on CI/staging |
| 215 MiB git garbage | COSMETIC | `git gc --aggressive --prune=now` |
