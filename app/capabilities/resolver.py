from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.capabilities.models import Capability, CapabilityType, RiskLevel
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
    def __init__(self, registry: CapabilityRegistry, safety_policy: SafetyPolicy) -> None:
        self.registry = registry
        self.safety_policy = safety_policy

    def resolve(self, task: str, requested_name: str, domain: str | None = None) -> CapabilityResolution:
        by_name = self.registry.resolve_by_name(requested_name)
        if by_name:
            return self._validate_candidate(by_name)

        candidate = self.registry.resolve_by_relevance(task=task, domain=domain)
        if candidate:
            return self._validate_candidate(candidate)

        return CapabilityResolution(
            path=ResolutionPath.GENERATED,
            capability=None,
            reason="No reusable capability found; generation path required",
        )

    def _validate_candidate(self, capability: Capability) -> CapabilityResolution:
        if capability.risk_level == RiskLevel.HIGH:
            return CapabilityResolution(
                path=ResolutionPath.HUMAN_CONFIRMATION,
                capability=capability,
                reason="High risk capability requires confirmation",
            )
        try:
            for domain in capability.allowed_domains:
                self.safety_policy.validate_skill("navigate_to_url", {"url": f"https://{domain}"})
        except SafetyViolationError as exc:
            return CapabilityResolution(path=ResolutionPath.FAIL, capability=capability, reason=str(exc))

        if capability.capability_type == CapabilityType.STABLE:
            return CapabilityResolution(path=ResolutionPath.STABLE, capability=capability, reason="Matched stable capability")
        return CapabilityResolution(path=ResolutionPath.LEARNED, capability=capability, reason="Matched learned/generated capability")
