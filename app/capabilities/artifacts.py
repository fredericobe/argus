from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CapabilityArtifactStore:
    """Filesystem artifact model for generated capabilities."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def persist(
        self,
        capability_id: str,
        metadata: dict[str, Any],
        source_code: str,
        sandbox_result: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> Path:
        cap_dir = self.root / "generated" / capability_id
        cap_dir.mkdir(parents=True, exist_ok=True)
        (cap_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
        (cap_dir / "source.py").write_text(source_code)
        (cap_dir / "sandbox_result.json").write_text(json.dumps(sandbox_result, indent=2, default=str))
        (cap_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2, default=str))
        if not (cap_dir / "usage_log.json").exists():
            (cap_dir / "usage_log.json").write_text("[]")
        return cap_dir

    def append_usage(self, capability_id: str, payload: dict[str, Any]) -> None:
        usage_path = self.root / "generated" / capability_id / "usage_log.json"
        if usage_path.exists():
            data = json.loads(usage_path.read_text())
        else:
            data = []
        data.append(payload)
        usage_path.write_text(json.dumps(data, indent=2, default=str))
