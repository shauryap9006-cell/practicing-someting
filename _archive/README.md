# _archive Master Manifest

Welcome to the RailTwin-X Codebase Archive.
In accordance with production cleanup standards: **Nothing is ever permanently deleted.**
Every removed whole file, legacy script, obsolete build artifact, dead component, and dependency is preserved here with its full original directory structure and restoration instructions.

---

## Archive Directory Layout

\_archive/
├── README.md                 # Master manifest (this file)
├── dead-code/                # Whole dead files, original relative paths preserved
│   ├── scripts/build_map.py
│   ├── temp_resultshield/
│   └── web/
├── legacy-scripts/           # One-off scripts, old tooling, completed migrations
│   ├── audit_probes/
│   ├── migrations/
│   └── scripts/diagnostics/
├── old-configs/              # Superseded config files
├── snippets/                 # Dead code blocks cut out of live files
├── unused-dependencies.md    # Manifest of removed packages and reinstall commands
└── reports/                  # Baseline audit outputs and final cleanup reports
\
---

## Master Manifest Table

| Original Path | Archive Path | Reason | Confidence | Date Archived | Restore Instructions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| \	emp_resultshield/\ | \_archive/dead-code/temp_resultshield/\ | Abandoned stress-test scaffold repository clone (60 files) | High | 2026-09-06 | \mv _archive/dead-code/temp_resultshield/ temp_resultshield/\ |
| \web/.next/\ | \_archive/dead-code/web/.next/\ | Obsolete Next.js build cache folder in a Vite application | High | 2026-09-06 | \mv _archive/dead-code/web/.next/ web/.next/\ |
| \scripts/build_map.py\ | \_archive/dead-code/scripts/build_map.py\ | 0-byte empty file | High | 2026-09-06 | \mv _archive/dead-code/scripts/build_map.py scripts/build_map.py\ |
| \web/src/components/landing/LiveMarqueeTicker.tsx\ | \_archive/dead-code/web/src/components/landing/LiveMarqueeTicker.tsx\ | Zero inbound imports across frontend | High | 2026-09-06 | \mv _archive/dead-code/web/src/components/landing/LiveMarqueeTicker.tsx web/src/components/landing/\ |
| \web/src/components/passenger/PassengerSatelliteMap.tsx\ | \_archive/dead-code/web/src/components/passenger/PassengerSatelliteMap.tsx\ | Zero inbound imports across frontend | High | 2026-09-06 | \mv _archive/dead-code/web/src/components/passenger/PassengerSatelliteMap.tsx web/src/components/passenger/\ |
| \web/src/components/ui/Input.tsx\ | \_archive/dead-code/web/src/components/ui/Input.tsx\ | Zero inbound imports across frontend | High | 2026-09-06 | \mv _archive/dead-code/web/src/components/ui/Input.tsx web/src/components/ui/\ |
| \web/src/components/ui/Skeleton.tsx\ | \_archive/dead-code/web/src/components/ui/Skeleton.tsx\ | Zero inbound imports across frontend | High | 2026-09-06 | \mv _archive/dead-code/web/src/components/ui/Skeleton.tsx web/src/components/ui/\ |
| \web/src/lib/firebase.ts\ | \_archive/dead-code/web/src/lib/firebase.ts\ | Dead integration file with hardcoded credentials | High | 2026-09-06 | \mv _archive/dead-code/web/src/lib/firebase.ts web/src/lib/\ |
| \udit_probes/\ | \_archive/legacy-scripts/audit_probes/\ | One-off AST system mapping and probe execution scripts | High | 2026-09-06 | \mv _archive/legacy-scripts/audit_probes/ audit_probes/\ |
| \scripts/diagnostics/\ | \_archive/legacy-scripts/scripts/diagnostics/\ | Completed one-off forensic diagnostic probes (p0_00 to p6_18) | High | 2026-09-06 | \mv _archive/legacy-scripts/scripts/diagnostics/ scripts/diagnostics/\ |
| \migrations/\ | \_archive/legacy-scripts/migrations/\ | Superseded root SQL migration files (canonical in \scripts/migrations/\) | High | 2026-09-06 | \mv _archive/legacy-scripts/migrations/ migrations/\ |
| \master_audit_v2_results.json\ | \_archive/reports/master_audit_v2_results.json\ | Historical audit report data dump | High | 2026-09-06 | \mv _archive/reports/master_audit_v2_results.json master_audit_v2_results.json\ |
| \scratch_audit_results.json\ | \_archive/reports/scratch_audit_results.json\ | Historical scratch audit dump | High | 2026-09-06 | \mv _archive/reports/scratch_audit_results.json scratch_audit_results.json\ |
| \.coverage\ | \_archive/reports/.coverage\ | Binary test coverage file from previous test run | High | 2026-09-06 | \mv _archive/reports/.coverage .coverage\ |
