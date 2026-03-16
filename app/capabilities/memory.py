from __future__ import annotations

import json
from pathlib import Path

from app.capabilities.models import CapabilityUsageRecord


class CapabilityMemory:
    """Memória simples (JSON) de execuções para permitir reuso determinístico."""
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[CapabilityUsageRecord] = []
        self._load()

    def record(self, record: CapabilityUsageRecord) -> None:
        self._records.append(record)
        self._save()

    def all_records(self) -> list[CapabilityUsageRecord]:
        return list(self._records)

    def successful_for_task(self, task: str) -> list[CapabilityUsageRecord]:
        normalized = task.lower()
        return [r for r in self._records if r.success and r.task.lower() == normalized]

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        payload = json.loads(self.storage_path.read_text())
        self._records = [CapabilityUsageRecord.model_validate(item) for item in payload]

    def _save(self) -> None:
        payload = [record.model_dump(mode="json") for record in self._records]
        self.storage_path.write_text(json.dumps(payload, indent=2))
