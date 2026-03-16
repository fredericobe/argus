from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.capabilities.models import Capability, CapabilityType, RiskLevel


class CapabilityRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, Capability] = {}
        self._by_name: dict[str, str] = {}
        self._usage: dict[str, int] = defaultdict(int)

    def register(self, capability: Capability) -> None:
        existing_id = self._by_name.get(capability.name)
        if existing_id and existing_id != capability.id:
            raise ValueError(f"Capability name already registered: {capability.name}")
        capability.updated_at = datetime.now(timezone.utc)
        self._by_id[capability.id] = capability
        self._by_name[capability.name] = capability.id

    def get(self, capability_id: str) -> Capability:
        return self._by_id[capability_id]

    def resolve_by_name(self, name: str) -> Capability | None:
        capability_id = self._by_name.get(name)
        if not capability_id:
            return None
        return self._by_id[capability_id]

    def list_capabilities(
        self,
        capability_type: CapabilityType | None = None,
        domain: str | None = None,
        max_risk: RiskLevel | None = None,
    ) -> list[Capability]:
        risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
        items = list(self._by_id.values())
        if capability_type:
            items = [c for c in items if c.capability_type == capability_type]
        if domain:
            items = [c for c in items if not c.allowed_domains or domain in c.allowed_domains]
        if max_risk:
            items = [c for c in items if risk_order[c.risk_level] <= risk_order[max_risk]]
        return sorted(items, key=lambda c: c.name)

    def resolve_by_relevance(self, task: str, domain: str | None = None) -> Capability | None:
        task_tokens = {token.lower() for token in task.split()}
        candidates = self.list_capabilities(domain=domain)
        best: tuple[int, Capability] | None = None
        for cap in candidates:
            text_tokens = {*(cap.name.lower().split("_")), *(cap.description.lower().split()), *[t.lower() for t in cap.tags]}
            score = len(task_tokens.intersection(text_tokens)) + self._usage[cap.id]
            if best is None or score > best[0]:
                best = (score, cap)
        if best and best[0] > 0:
            return best[1]
        return None

    def mark_usage(self, capability_id: str) -> None:
        self._usage[capability_id] += 1
