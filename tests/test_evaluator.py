from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxResult
from app.capabilities.models import Capability, CapabilityStatus, CapabilityType, ImplementationKind
from app.safety.safety_policy import SafetyPolicy


def _cap(domains: list[str]) -> Capability:
    return Capability(
        id="c1",
        name="gen",
        description="generated",
        status=CapabilityStatus.GENERATED_TEMPORARY,
        capability_type=CapabilityType.GENERATED_TEMPORARY,
        implementation_kind=ImplementationKind.GENERATED_CODE,
        implementation_ref="run",
        allowed_domains=domains,
    )


def test_evaluator_accepts_success_with_evidence_and_marks_promotable() -> None:
    evaluator = CapabilityEvaluator(SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=2))
    result = evaluator.evaluate(_cap(["amazon.com"]), SandboxResult(True, {"evidence": ["a"]}))
    assert result.accepted is True
    assert result.promotable is True


def test_evaluator_rejects_missing_evidence_and_unsafe_domain_with_reason() -> None:
    evaluator = CapabilityEvaluator(SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=2))
    missing = evaluator.evaluate(_cap(["amazon.com"]), SandboxResult(True, {}))
    assert missing.accepted is False
    assert "missing evidence" in missing.reason

    unsafe = evaluator.evaluate(_cap(["evil.com"]), SandboxResult(True, {"evidence": ["x"]}))
    assert unsafe.accepted is False
    assert "unsafe domain usage" in unsafe.reason
