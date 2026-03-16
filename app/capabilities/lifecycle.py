from app.capabilities.models import Capability, CapabilityStatus, CapabilityType


class CapabilityLifecycle:
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

    def is_reusable(self, capability: Capability) -> bool:
        return capability.status in {
            CapabilityStatus.STABLE,
            CapabilityStatus.APPROVED_STABLE,
            CapabilityStatus.GENERATED_CANDIDATE,
            CapabilityStatus.GENERATED_TEMPORARY,
        }
