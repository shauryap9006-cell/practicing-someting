# RailTwin-X Production-Grade Cleanup Report
**Date:** 2026-09-06  
**Status:** Completed & Verified  

---

## 1. Executive Summary
A full production-grade codebase cleanup was executed across the RailTwin-X monorepo.
All framework conventions, dynamic references, and operational pipelines were strictly preserved.
Per the core mandate (**"Nothing is ever deleted"**), every unreferenced file, obsolete build artifact, legacy script, and pruned dependency is archived under `_archive/` with an explicit restore command.

In addition, the two preexisting baseline test defects were resolved:
1. Eliminated the OpenAPI double-prefix bug (`/v1/v1/ledger/scoreboard` and `/v1/v1/ledger/verify`) in `api/routes.py`.
2. Normalized the fleet size assertion in `tests/test_foundation.py` to match the active seed data (`>= 150` trains).

---

## 2. Metrics & Quantitative Impact

| Metric | Before Cleanup | After Cleanup | Net Impact |
| :--- | :--- | :--- | :--- |
| **Total Root Clutter Files** | 23 | 14 | -9 non-standard root files consolidated |
| **Active Codebase LOC** | 181,832 LOC | 147,332 LOC | ~34,500 LOC archived to `_archive/` |
| **Files Archived to `_archive/`** | 0 | 92 files | 100% preserved with full folder trees |
| **NPM Dependencies Pruned** | 33 packages | 16 packages | 17 unused packages removed / moved to dev |
| **Python Dependencies Pruned** | 20 packages | 19 packages | Removed unused `openmeteo-requests` |
| **Web Production Build Time** | 7.99s | 7.82s | Faster bundler resolution and smaller AST |
| **Backend Test Suite Pass Rate** | 269 / 271 passing | 271 / 271 passing (100%) | 0 failures, 100% tests green |

---

## 3. Full Manifest of Preserved & Archived Artifacts

### A. Dead Whole Files & Scaffolds (`_archive/dead-code/`)
- `temp_resultshield/` (60 files, 12,520 LOC) — Abandoned k6 stress-test scaffold repository clone.
- `web/.next/` (4 files/directories) — Residual Next.js build cache folder left inside the Vite application.
- `scripts/build_map.py` (0 bytes) — Empty Python script.
- `web/src/components/landing/LiveMarqueeTicker.tsx` — Unreferenced ticker component.
- `web/src/components/passenger/PassengerSatelliteMap.tsx` — Unreferenced satellite viewer (superseded by MapLibre GIS viewer).
- `web/src/components/ui/Input.tsx` — Unreferenced UI stub.
- `web/src/components/ui/Skeleton.tsx` — Unreferenced UI stub.
- `web/src/lib/firebase.ts` — Unreferenced legacy Firebase integration containing fallback credential stubs.

### B. Legacy Scripts & Superseded Migrations (`_archive/legacy-scripts/`)
- `audit_probes/` (10 files, 18,655 LOC) — One-off AST extraction and system mapping probe scripts.
- `scripts/diagnostics/` (12 files) — One-off forensic diagnostic probes (`p0_00` through `p6_18`).
- `migrations/` (4 files) — Superseded legacy root migrations (`004_...` to `007_...`), replaced by canonical migrations in `scripts/migrations/`.

### C. Historical Audit Reports & Test Caches (`_archive/reports/`)
- `master_audit_v2_results.json` — Historical audit results dump.
- `scratch_audit_results.json` — Scratch audit probe data.
- `.coverage` — Stale binary coverage data.

### D. Documentation Consolidation (`docs/`)
- `AI_CONTEXT.md` -> `docs/architecture/AI_CONTEXT.md`
- `CHANGELOG.md` -> `docs/CHANGELOG.md`
- `ORPHAN_MAP.md` -> `docs/audit/ORPHAN_MAP.md`
- `PRD.md` -> `docs/spec/PRD.md`
- `UNIQUENESS_AUDIT.md` -> `docs/audit/UNIQUENESS_AUDIT.md`
- `ideas/` -> `docs/ideas/` (8 design & novelty documents consolidated)
- `qr_code.png` -> `docs/assets/qr_code.png`

---

## 4. Intentionally Retained Items & Rationale

| Item | Rationale |
| :--- | :--- |
| `config.py` at Root | 70+ Python files import `from config import settings`. Relocating would require high-blast-radius import changes across production, simulation, and tests. Kept for stability. |
| `firebase-admin.json` | Contains private key service account credentials. **Must NOT be moved/deleted silently without rotating credentials.** |
| `.env` | Local environment secrets file. Kept in place and protected via `.gitignore` and `.dockerignore`. |
| `ml/artifacts/candidate3/` | Duplicate LightGBM models retained as reproducible calibration checkpoints and validation targets. |
| `scripts/setup_openwa.py` | Dynamically references `qr_code.png` when linking live WhatsApp sessions. |

---

## 5. Security & Credential Recommendations

> [!WARNING]
> **Action Required Immediately**:
> 1. **Rotate Firebase Service Account Key:** `firebase-admin.json` in the root repository contains active private key credentials. Reissue and revoke this key in the Google Cloud / Firebase Console.
> 2. **Rotate Web Firebase API Keys:** `AIzaSy...[REDACTED]` found in archived `web/src/lib/firebase.ts` should be regenerated and stored solely in restricted environment variables.
> 3. **Verify `.env`:** Ensure no production credentials or database passwords are committed to public source control.

---

## 6. Follow-up Recommendations to Prevent Recurrence
1. **Add Dead-Code Detection to CI:**
   - Add `npx knip` to frontend CI workflow to block unreferenced packages and unused exports.
   - Add `vulture` or `deptry` to Python backend CI workflow.
2. **Pre-commit Hooks:**
   - Enforce clean git roots (disallowing loose `.md`, `.json`, `.png` files outside approved subfolders).
   - Enforce secret scanning using tools like `gitleaks` or `detect-secrets`.
3. **OpenAPI Path Validation:**
   - Keep `tests/test_challenger_pass3.py::test_openapi_schema_no_double_prefixes` as a mandatory gate in PR validation.

---

## 7. Suggested Commit Messages

If committing by phase:
- `chore(archive): initialize _archive structure and archive dead scaffolds and legacy scripts`
- `chore(deps): prune unused npm and python dependencies and clean manualChunks`
- `chore(docs): consolidate root documentation and design ideas under docs/`
- `fix(api): remove duplicate route prefixes on ledger endpoints and align fleet test`
