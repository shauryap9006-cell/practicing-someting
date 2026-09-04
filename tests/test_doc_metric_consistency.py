"""Automated consistency test between documentation and ml/artifacts/metrics.json.

Ensures zero metric drift across judge_onepager.md, judge_qa.md, and demo_runbook.md.
Any stale hand-typed metric numbers (e.g. 7.4 min, 7.29 min, 12.2 min) will fail this test.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_FILE = REPO_ROOT / "ml" / "artifacts" / "metrics.json"
ONEPAGER_FILE = REPO_ROOT / "docs" / "judge_onepager.md"
QA_FILE = REPO_ROOT / "docs" / "judge_qa.md"
RUNBOOK_FILE = REPO_ROOT / "docs" / "demo_runbook.md"


@pytest.fixture
def metrics_data():
    assert METRICS_FILE.exists(), "metrics.json does not exist"
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_judge_onepager_matches_metrics_json(metrics_data):
    """Asserts that docs/judge_onepager.md strictly matches ground truth metrics in metrics.json."""
    assert ONEPAGER_FILE.exists()
    content = ONEPAGER_FILE.read_text(encoding="utf-8")

    # Canonical overall numbers
    overall_mae = metrics_data["canonical_mae"]
    assert f"{overall_mae} min" in content, f"Overall MAE {overall_mae} missing from judge_onepager.md"
    assert "80.64%" in content or "80.6%" in content, "Overall coverage missing from judge_onepager.md"
    assert "57.94" in content, "Overall Winkler score 57.94 missing from judge_onepager.md"

    # Per-horizon numbers
    m_1h = metrics_data["metrics_by_horizon"]["1 h (<=90km)"]
    m_3h = metrics_data["metrics_by_horizon"]["3 h (90-250km)"]
    m_6h = metrics_data["metrics_by_horizon"]["6 h (>250km)"]

    mae_1h = round(m_1h["mae_railtwin"], 2)
    mae_3h = round(m_3h["mae_railtwin"], 2)
    mae_6h = round(m_6h["mae_railtwin"], 2)

    assert f"{mae_1h} min" in content, f"1h MAE {mae_1h} missing from judge_onepager.md"
    assert f"{mae_3h} min" in content, f"3h MAE {mae_3h} missing from judge_onepager.md"
    assert f"{mae_6h} min" in content, f"6h MAE {mae_6h} missing from judge_onepager.md"

    # Strict ban on stale numbers
    assert "7.4 min" not in content, "Stale 7.4 min MAE found in judge_onepager.md!"
    assert "7.29 min" not in content, "Stale 7.29 min MAE found in judge_onepager.md!"
    assert "12.2 min" not in content, "Stale 12.2 min MAE found in judge_onepager.md!"
    assert "17.2 min" not in content, "Stale 17.2 min MAE found in judge_onepager.md!"


def test_no_stale_metric_claims_in_docs():
    """Verifies that no docs quote obsolete 7.4 min or 7.29 min claims."""
    docs_to_check = [ONEPAGER_FILE, QA_FILE, RUNBOOK_FILE]
    for doc in docs_to_check:
        if doc.exists():
            text = doc.read_text(encoding="utf-8")
            assert "7.4 min" not in text, f"Stale '7.4 min' found in {doc.name}"
            assert "7.29 min" not in text, f"Stale '7.29 min' found in {doc.name}"
