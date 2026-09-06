"""Generate the serving-model SHA-256 inventory after an intentional retrain."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import settings
from ml.artifact_integrity import INTEGRITY_FILE_NAME, MODEL_ARTIFACT_NAMES, sha256_file


def main() -> None:
    artifacts_dir = settings.ARTIFACTS_DIR
    missing = [name for name in MODEL_ARTIFACT_NAMES if not (artifacts_dir / name).is_file()]
    if missing:
        raise SystemExit(f"Cannot create inventory; missing artifacts: {', '.join(missing)}")

    inventory = {
        "algorithm": "sha256",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {name: sha256_file(artifacts_dir / name) for name in MODEL_ARTIFACT_NAMES},
    }
    (artifacts_dir / INTEGRITY_FILE_NAME).write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {artifacts_dir / INTEGRITY_FILE_NAME}")


if __name__ == "__main__":
    main()
