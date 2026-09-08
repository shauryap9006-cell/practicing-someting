"""RailTwin-X — PII Retention & Purge Job (DPDP Act 2023 Compliance).

Per Digital Personal Data Protection Act 2023 (India) requirements:
1. Personal data (names, PNR numbers, phone numbers, identity proofs, notification payloads)
   must not be stored indefinitely and must adhere to purpose limitation.
2. Identifiable PII in delay_certificates older than PII_RETENTION_DAYS (default 90) is redacted:
   - issued_to_name -> 'REDACTED'
   - pnr_no -> SHA-256 hash prefix (retains verifiable integrity without exposing cleartext PNR)
3. Expired logs in notification_log are purged past retention.
4. Claimed claimant PII in lost_and_found is redacted past retention.
5. Default mode is DRY-RUN (safe, audit-only). Explicit --apply required to write changes.
6. Execution is strictly idempotent.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import settings
from data.db import Database, get_db
from engine.clocks import ist_now

logger = logging.getLogger("railtwin.privacy")


def hash_pnr(pnr: Optional[str]) -> Optional[str]:
    """Hashes a PNR number using SHA-256 prefix for pseudonymized verification under DPDP Act 2023."""
    if not pnr:
        return None
    if pnr.startswith("SHA256:"):
        return pnr
    h = hashlib.sha256(pnr.encode("utf-8")).hexdigest()[:16]
    return f"SHA256:{h}"


def purge_expired_pii(
    db: Optional[Database] = None,
    days: Optional[int] = None,
    apply: bool = False,
    now_dt: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Scans and optionally redacts/purges personal data older than the retention window.

    Args:
        db: Database instance (defaults to get_db()).
        days: Retention period in days (defaults to settings.PII_RETENTION_DAYS).
        apply: When True, writes updates to the database. When False, performs a dry-run.
        now_dt: Optional explicit current datetime for testing.

    Returns:
        Summary dict containing execution statistics and affected row counts.
    """
    if db is None:
        db = get_db()

    retention_days = days if days is not None else settings.PII_RETENTION_DAYS
    if retention_days < 1:
        raise ValueError(f"Retention days must be >= 1, got {retention_days}")

    now = now_dt or ist_now()
    cutoff_dt = now - datetime.timedelta(days=retention_days)
    cutoff_iso = cutoff_dt.isoformat()

    stats: Dict[str, Any] = {
        "apply": apply,
        "dry_run": not apply,
        "retention_days": retention_days,
        "current_time_ist": now.isoformat(),
        "cutoff_time_ist": cutoff_iso,
        "delay_certificates": 0,
        "notification_log": 0,
        "lost_and_found": 0,
        "total_affected": 0,
    }

    conn = db.get_connection()
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
    finally:
        conn.close()

    with db.transaction() as cur:
        # 1. Delay Certificates: redact passenger name and pseudonymize PNR
        if "delay_certificates" in tables:
            cur.execute(
                """
                SELECT id, cert_no, pnr_no, issued_to_name, issued_at
                FROM delay_certificates
                WHERE issued_at < ?
                  AND (issued_to_name != 'REDACTED' OR (pnr_no IS NOT NULL AND pnr_no NOT LIKE 'SHA256:%'));
                """,
                (cutoff_iso,),
            )
            expired_certs = cur.fetchall()
            stats["delay_certificates"] = len(expired_certs)

            if apply and expired_certs:
                for row in expired_certs:
                    row_id = row["id"]
                    curr_pnr = row["pnr_no"]
                    new_pnr = hash_pnr(curr_pnr)
                    cur.execute(
                        """
                        UPDATE delay_certificates
                        SET issued_to_name = 'REDACTED',
                            pnr_no = ?
                        WHERE id = ?;
                        """,
                        (new_pnr, row_id),
                    )
                logger.info(
                    "Redacted %d expired delay certificate(s) older than %s",
                    len(expired_certs),
                    cutoff_iso,
                )

        # 2. Notification Log: purge dispatch audit logs past retention
        if "notification_log" in tables:
            cur.execute(
                """
                SELECT COUNT(*) FROM notification_log
                WHERE sent_at IS NOT NULL AND sent_at < ?;
                """,
                (cutoff_iso,),
            )
            expired_notifs = int(cur.fetchone()[0])
            stats["notification_log"] = expired_notifs

            if apply and expired_notifs > 0:
                cur.execute(
                    """
                    DELETE FROM notification_log
                    WHERE sent_at IS NOT NULL AND sent_at < ?;
                    """,
                    (cutoff_iso,),
                )
                logger.info(
                    "Purged %d expired notification log entry/entries older than %s",
                    expired_notifs,
                    cutoff_iso,
                )

        # 3. Lost & Found Register: redact claimant passenger PII for claimed items
        if "lost_and_found" in tables:
            cur.execute(
                """
                SELECT COUNT(*) FROM lost_and_found
                WHERE status = 'CLAIMED'
                  AND (claimed_at < ? OR (claimed_at IS NULL AND found_at < ?))
                  AND (claimant_name != 'REDACTED' OR claimant_phone != 'REDACTED' OR claimant_id_proof != 'REDACTED');
                """,
                (cutoff_iso, cutoff_iso),
            )
            expired_claims = int(cur.fetchone()[0])
            stats["lost_and_found"] = expired_claims

            if apply and expired_claims > 0:
                cur.execute(
                    """
                    UPDATE lost_and_found
                    SET claimant_name = 'REDACTED',
                        claimant_id_proof = 'REDACTED',
                        claimant_phone = 'REDACTED'
                    WHERE status = 'CLAIMED'
                      AND (claimed_at < ? OR (claimed_at IS NULL AND found_at < ?))
                      AND (claimant_name != 'REDACTED' OR claimant_phone != 'REDACTED' OR claimant_id_proof != 'REDACTED');
                    """,
                    (cutoff_iso, cutoff_iso),
                )
                logger.info(
                    "Redacted %d expired claimant PII record(s) older than %s",
                    expired_claims,
                    cutoff_iso,
                )

    stats["total_affected"] = (
        stats["delay_certificates"] + stats["notification_log"] + stats["lost_and_found"]
    )

    action_label = "PURGED/REDACTED" if apply else "FOUND (DRY-RUN)"
    logger.info(
        "PII Retention Job [%s]: %d delay_certs, %d notification_logs, %d lost_and_found (Total: %d)",
        action_label,
        stats["delay_certificates"],
        stats["notification_log"],
        stats["lost_and_found"],
        stats["total_affected"],
    )

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RailTwin-X PII Purge & Redaction CLI (DPDP Act 2023)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply redaction/purges (default is DRY-RUN, no changes written)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Explicitly request dry-run mode (audit-only)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"Retention period in days (default: {settings.PII_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help=f"Path to SQLite database (default: {settings.DB_PATH})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose logging output",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    should_apply = args.apply and not args.dry_run
    db = Database(Path(args.db_path)) if args.db_path else get_db()

    print(
        f"=== RailTwin-X PII Retention Purge ({'APPLY' if should_apply else 'DRY-RUN'}) ==="
    )
    res = purge_expired_pii(
        db=db,
        days=args.days,
        apply=should_apply,
    )

    print(f"Retention Window : {res['retention_days']} days")
    print(f"Cutoff Timestamp : {res['cutoff_time_ist']}")
    print(f"Mode             : {'APPLIED (DB updated)' if should_apply else 'DRY-RUN (no changes made)'}")
    print("--------------------------------------------------")
    print(f"Delay Certificates Redacted : {res['delay_certificates']}")
    print(f"Notification Logs Purged    : {res['notification_log']}")
    print(f"Lost & Found PII Redacted   : {res['lost_and_found']}")
    print(f"Total Affected Records      : {res['total_affected']}")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
