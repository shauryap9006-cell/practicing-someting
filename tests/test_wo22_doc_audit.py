"""WO-22 Verification Gate: Docs Integrity.

Verifies that self-assigned audit scores in REMEDIATION-REPORT.md,
REMEDIATION.md, and CHANGE-REPORT.md are annotated as internally generated,
and point to the external GRANDMASTER AUDIT PROTOCOL v3.1 (score: 60/100)
as the sole authoritative score of record.
"""

from pathlib import Path


def test_wo22_doc_audit_integrity():
    repo_root = Path(__file__).resolve().parent.parent

    # 1. CHANGE-REPORT.md
    change_report = (repo_root / "CHANGE-REPORT.md").read_text(encoding="utf-8")
    assert "v3.1" in change_report
    assert "60/100" in change_report
    assert "Internal self-assigned claim" in change_report or "internally generated" in change_report

    # 2. REMEDIATION-REPORT.md
    rem_report = (repo_root / "REMEDIATION-REPORT.md").read_text(encoding="utf-8")
    assert "v3.1" in rem_report
    assert "60/100" in rem_report
    assert "internally generated, self-assigned estimations" in rem_report or "internal claim" in rem_report

    # 3. REMEDIATION.md
    rem_md = (repo_root / "REMEDIATION.md").read_text(encoding="utf-8")
    assert "v3.1" in rem_md
    assert "60/100" in rem_md
    assert "internal claims" in rem_md or "internally generated" in rem_md
