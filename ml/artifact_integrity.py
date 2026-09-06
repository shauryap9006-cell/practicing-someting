"""Integrity checks for model artifacts loaded by the serving process."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


MODEL_ARTIFACT_NAMES = (
    "model_direct_q10.txt",
    "model_direct_q50.txt",
    "model_direct_q90.txt",
    "model_delta_q10.txt",
    "model_delta_q50.txt",
    "model_delta_q90.txt",
    "model_gru_challenger.pt",
    "model_lr_benchmark.pkl",
)
INTEGRITY_FILE_NAME = "artifact_integrity.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifacts(artifacts_dir: Path, required_names: Iterable[str] = MODEL_ARTIFACT_NAMES) -> tuple[bool, list[str]]:
    """Verify every serving artifact against the committed inventory.

    The inventory is packaged with the application image. A missing inventory,
    missing model, path traversal entry, or digest mismatch is a readiness failure.
    """
    inventory_path = artifacts_dir / INTEGRITY_FILE_NAME
    if not inventory_path.is_file():
        return False, [f"missing {INTEGRITY_FILE_NAME}"]

    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"invalid {INTEGRITY_FILE_NAME}: {exc}"]

    expected = inventory.get("files") if isinstance(inventory, dict) else None
    if not isinstance(expected, dict):
        return False, [f"invalid {INTEGRITY_FILE_NAME}: files must be an object"]

    root = artifacts_dir.resolve()
    failures: list[str] = []
    for name in required_names:
        expected_hash = expected.get(name)
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            failures.append(f"missing digest for {name}")
            continue

        candidate = (artifacts_dir / name).resolve()
        if candidate.parent != root:
            failures.append(f"invalid artifact path {name}")
            continue
        if not candidate.is_file():
            failures.append(f"missing {name}")
            continue
        if sha256_file(candidate).lower() != expected_hash.lower():
            failures.append(f"digest mismatch for {name}")

    return not failures, failures
