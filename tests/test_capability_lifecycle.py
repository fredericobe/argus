from app.capabilities.lifecycle import CapabilityLifecycle
from app.capabilities.models import (
    Capability,
    CapabilityStatus,
    CapabilityType,
    ImplementationKind,
)


def _temp_cap() -> Capability:
    return Capability(
        id="g1",
        name="gen",
        description="generated",
        status=CapabilityStatus.GENERATED_TEMPORARY,
        capability_type=CapabilityType.GENERATED_TEMPORARY,
        implementation_kind=ImplementationKind.GENERATED_CODE,
        implementation_ref="run",
    )


def test_lifecycle_candidate_reject_and_promote() -> None:
    lifecycle = CapabilityLifecycle()
    cap = _temp_cap()

    lifecycle.mark_candidate(cap)
    assert cap.status == CapabilityStatus.GENERATED_CANDIDATE

    lifecycle.reject(cap, "bad evidence")
    assert cap.status == CapabilityStatus.REJECTED
    assert lifecycle.is_reusable(cap) is False

    cap = _temp_cap()
    lifecycle.promote_to_stable(cap)
    assert cap.status == CapabilityStatus.APPROVED_STABLE
