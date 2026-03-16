from __future__ import annotations

from dataclasses import dataclass

from app.capabilities.models import Capability, CapabilityStatus, CapabilityType


@dataclass(slots=True)
class PromotionPolicy:
    min_successful_runs: int = 3
    min_evaluator_score: float = 0.8
    max_safety_violations: int = 0
    require_evidence: bool = True


class CapabilityLifecycle:
    def __init__(self, policy: PromotionPolicy | None = None) -> None:
        self.policy = policy or PromotionPolicy()

    def mark_candidate(self, capability: Capability) -> Capability:
        capability.status = CapabilityStatus.GENERATED_CANDIDATE
        capability.capability_type = CapabilityType.GENERATED_CANDIDATE
        return capability

    def reject(self, capability: Capability, reason: str) -> Capability:
        capability.status = CapabilityStatus.REJECTED
        capability.metadata["rejection_reason"] = reason
        return capability

    def promote_to_stable(self, capability: Capability) -> Capability:
        capability.status = CapabilityStatus.APPROVED_STABLE
        capability.capability_type = CapabilityType.LEARNED
        capability.metadata["promoted"] = True
        return capability

    def can_promote(
        self,
        successful_runs: int,
        evaluator_score: float,
        safety_violations: int,
        evidence_complete: bool,
    ) -> bool:
        if successful_runs < self.policy.min_successful_runs:
            return False
        if evaluator_score < self.policy.min_evaluator_score:
            return False
        if safety_violations > self.policy.max_safety_violations:
            return False
        if self.policy.require_evidence and not evidence_complete:
            return False
        return True

    def is_reusable(self, capability: Capability) -> bool:
        return capability.status in {
            CapabilityStatus.STABLE,
            CapabilityStatus.APPROVED_STABLE,
            CapabilityStatus.GENERATED_CANDIDATE,
            CapabilityStatus.GENERATED_TEMPORARY,
        }
