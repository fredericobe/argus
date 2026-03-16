from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxResult
from app.capabilities.models import Capability, CapabilityStatus, CapabilityType, ImplementationKind
from app.safety.safety_policy import SafetyPolicy


def _cap(domains):
    return Capability(
        id="g",
        name="gen",
        description="gen",
        status=CapabilityStatus.GENERATED_TEMPORARY,
        capability_type=CapabilityType.GENERATED_TEMPORARY,
        implementation_kind=ImplementationKind.GENERATED_CODE,
        implementation_ref="run",
        allowed_domains=domains,
    )


def test_generated_capability_cannot_bypass_allowlist_or_blocklist() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=["bad.com"], max_steps=3)
    evaluator = CapabilityEvaluator(policy)

    blocked = evaluator.evaluate(_cap(["bad.com"]), SandboxResult(True, {"evidence": ["x"]}))
    assert blocked.accepted is False

    undeclared = evaluator.evaluate(_cap(["evil.com"]), SandboxResult(True, {"evidence": ["x"]}))
    assert undeclared.accepted is False
