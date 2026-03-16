from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.capabilities.memory import CapabilityMemory
from app.capabilities.models import Capability, CapabilityStatus, CapabilityType, RiskLevel
from app.capabilities.registry import CapabilityRegistry
from app.safety.safety_policy import SafetyPolicy, SafetyViolationError


class ResolutionPath(str, Enum):
    STABLE = "stable"
    LEARNED = "learned"
    GENERATED = "generated"
    HUMAN_CONFIRMATION = "human_confirmation"
    FAIL = "fail"


@dataclass(slots=True)
class CapabilityResolution:
    path: ResolutionPath
    capability: Capability | None
    reason: str


class CapabilityResolver:
    def __init__(self, registry: CapabilityRegistry, safety_policy: SafetyPolicy, memory: CapabilityMemory | None = None) -> None:
        self.registry = registry
        self.safety_policy = safety_policy
        self.memory = memory

    def resolve(self, task: str, requested_name: str, domain: str | None = None) -> CapabilityResolution:
        by_name = self.registry.resolve_by_name(requested_name)
        if by_name:
            return self._validate_candidate(by_name)

        if self.memory:
            for rec in self.memory.successful_for_task(task):
                candidate = self.registry.resolve_by_name(requested_name)
                if not candidate:
                    try:
                        candidate = self.registry.get(rec.capability_id)
                    except KeyError:
                        continue
                if candidate.status != CapabilityStatus.REJECTED:
                    return self._validate_candidate(candidate)

        candidate = self.registry.resolve_by_relevance(task=task, domain=domain)
        if candidate:
            return self._validate_candidate(candidate)

        return CapabilityResolution(ResolutionPath.GENERATED, None, "No reusable capability found; generation path required")

    def _validate_candidate(self, capability: Capability) -> CapabilityResolution:
        if capability.status == CapabilityStatus.REJECTED:
            return CapabilityResolution(ResolutionPath.FAIL, capability, "Capability has been rejected")
        if capability.risk_level == RiskLevel.HIGH:
            return CapabilityResolution(ResolutionPath.HUMAN_CONFIRMATION, capability, "High risk capability requires confirmation")
        try:
            for domain in capability.allowed_domains:
                self.safety_policy.validate_skill("navigate_to_url", {"url": f"https://{domain}"})
        except SafetyViolationError as exc:
            return CapabilityResolution(ResolutionPath.FAIL, capability, str(exc))

        if capability.capability_type == CapabilityType.STABLE:
            return CapabilityResolution(ResolutionPath.STABLE, capability, "Matched stable capability")
        return CapabilityResolution(ResolutionPath.LEARNED, capability, "Matched learned/generated capability")
