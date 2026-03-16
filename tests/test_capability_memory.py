from pathlib import Path

from app.capabilities.memory import CapabilityMemory
from app.capabilities.models import CapabilityUsageRecord


def test_memory_records_and_reuses_success_and_rejects_failed(tmp_path: Path) -> None:
    memory = CapabilityMemory(tmp_path / "memory.json")
    memory.record(CapabilityUsageRecord(capability_id="c1", task="check order", success=True))
    memory.record(CapabilityUsageRecord(capability_id="c2", task="check order", success=False))

    successful = memory.successful_for_task("check order")
    assert [r.capability_id for r in successful] == ["c1"]

    loaded = CapabilityMemory(tmp_path / "memory.json")
    assert len(loaded.all_records()) == 2
