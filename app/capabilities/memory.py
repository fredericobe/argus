from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.capabilities.models import CapabilityUsageRecord


class CapabilityMemory:
    """Persistent JSON memory for conservative capability reuse."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[CapabilityUsageRecord] = []
        self._load()

    @staticmethod
    def normalize_task_signature(task: str) -> str:
        normalized = " ".join(task.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def record(self, record: CapabilityUsageRecord) -> None:
        self._records.append(record)
        self._save()

    def all_records(self) -> list[CapabilityUsageRecord]:
        return list(self._records)

    def successful_for_task(self, task: str) -> list[CapabilityUsageRecord]:
        sig = self.normalize_task_signature(task)
        return [r for r in self._records if r.success and ((r.task_signature and r.task_signature == sig) or (not r.task_signature and self.normalize_task_signature(r.task) == sig))]

    def confidence_for_capability(self, capability_id: str) -> float:
        records = [r for r in self._records if r.capability_id == capability_id]
        if not records:
            return 0.0
        successes = sum(1 for r in records if r.success)
        avg_score = sum(r.evaluator_score for r in records) / len(records)
        return round((successes / len(records)) * 0.6 + avg_score * 0.4, 3)

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        payload = json.loads(self.storage_path.read_text())
        self._records = [CapabilityUsageRecord.model_validate(item) for item in payload]

    def _save(self) -> None:
        payload = [record.model_dump(mode="json") for record in self._records]
        self.storage_path.write_text(json.dumps(payload, indent=2))
