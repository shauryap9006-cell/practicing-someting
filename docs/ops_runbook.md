# 🛠️ RailTwin-X Operations & Maintenance Runbook

Operational procedures, routine maintenance tasks, and compliance controls for RailTwin-X production and staging environments.

---

## 1. Architecture Constraints & Process Model

RailTwin-X operates under a **single-worker process architecture** (`--workers 1`):
- All in-process state machines (simulated clock, kinematic state vector, dead-reckoning filters, WebSocket/SSE subscribers, in-memory rate limiters, and idempotency caches) require a single unified Python process.
- Horizontal scaling across multi-worker uvicorn instances is prohibited without external distributed caching (e.g. Redis).
- Production launcher:
  ```bash
  uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
  # or
  make api-prod
  ```

---

## 2. DPDP Act 2023 Compliance & PII Retention

### Regulatory Framework
Under India's **Digital Personal Data Protection Act (DPDP Act 2023)**, passenger and personnel identifying information must adhere to **purpose limitation** and **storage limitation** mandates. Personal data must not be stored indefinitely once the operational purpose of issuance or notification has concluded.

### Configured Policy
- **Setting**: `PII_RETENTION_DAYS` (default: `90` days).
- **Environment Override**: `RAILTWIN_PII_RETENTION_DAYS=90` in `/etc/railtwin/.env`.

### Automated Redaction & Purge Scope
| Data Store | Target Column(s) | Action Past Cutoff | Rationale |
|---|---|---|---|
| `delay_certificates` | `issued_to_name` | Replaced with `"REDACTED"` | Removes passenger identity |
| `delay_certificates` | `pnr_no` | Replaced with `SHA256:<hash_16>` | Pseudonymized verification preserved without exposing cleartext PNR |
| `notification_log` | All columns | Deleted (`DELETE FROM notification_log WHERE sent_at < ?`) | Outbound dispatch logs purged |
| `lost_and_found` | `claimant_name`, `claimant_phone`, `claimant_id_proof` | Replaced with `"REDACTED"` | Claimant PII removed for settled items |

### Cron Schedule
Schedule the purge job via system crontab on the host server:

```cron
# Edit crontab with: crontab -e
# RailTwin-X: Nightly DPDP Act 2023 PII Retention Purge at 02:00 IST
0 2 * * * cd /opt/railtwin && /opt/railtwin/.venv/bin/python -m scripts.purge_expired_pii --apply >> /var/log/railtwin/pii-purge.log 2>&1
```

### Manual Execution & Verification
```bash
# Dry-run audit (reports affected records without writing to DB):
make purge-pii-dry
# or
python -m scripts.purge_expired_pii --dry-run

# Apply purge immediately:
make purge-pii
# or
python -m scripts.purge_expired_pii --apply
```

---

## 3. Database Migrations & Rollback Operations

The migration system (`data/db.py`) supports forward migrations and paired down-migrations:

```bash
# Check migration status (applied vs pending):
python data/db.py --status

# Apply all pending migrations:
python data/db.py --migrate

# Roll back the most recent migration:
python data/db.py --downgrade 1

# Roll back to a specific version:
python data/db.py --downgrade-to 15
```

---

## 4. Backups & Disaster Recovery

- Automated SQLite online backups:
  ```bash
  python scripts/backup_db.py
  ```
- Backups are stored in `data/backups/` and verified with SQLite integrity checks.
