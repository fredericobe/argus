from pathlib import Path

from app.builder.builder import CapabilityBuilder
from app.builder.code_provider import StubCodeGenerationProvider
from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxRunner
from app.capabilities.lifecycle import CapabilityLifecycle, PromotionPolicy
from app.capabilities.memory import CapabilityMemory
from app.capabilities.models import Capability, CapabilityStatus, CapabilityType, ImplementationKind
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.resolver import CapabilityResolver, ResolutionPath
from app.safety.safety_policy import SafetyPolicy


class UnsafeProvider:
    def generate(self, spec):
        from app.builder.code_provider import GeneratedCapabilityPackage

        return GeneratedCapabilityPackage(
            capability_id="generated::unsafe",
            declared_domains=spec.allowed_domains,
            source_code="import os\ndef run(arguments):\n    return {'status':'ok'}\n",
            entrypoint="run",
            manifest={"name": spec.name},
        )


def _cap(name: str, status: CapabilityStatus, ctype: CapabilityType, domains: list[str]) -> Capability:
    return Capability(
        id=f"id-{name}",
        name=name,
        description=name,
        status=status,
        capability_type=ctype,
        implementation_kind=ImplementationKind.GENERATED_CODE,
        implementation_ref="run",
        allowed_domains=domains,
    )


def test_sandbox_blocks_disallowed_imports() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    builder = CapabilityBuilder(UnsafeProvider(), SandboxRunner(True, 1), CapabilityEvaluator(policy), CapabilityLifecycle())
    result = builder.build("task", "unsafe", ["amazon.com"])
    assert result.capability.status == CapabilityStatus.REJECTED


def test_rejected_capability_never_reused() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    registry = CapabilityRegistry()
    rejected = _cap("bad", CapabilityStatus.REJECTED, CapabilityType.GENERATED_CANDIDATE, ["amazon.com"])
    registry.register(rejected)
    resolver = CapabilityResolver(registry, policy)
    resolution = resolver.resolve("bad", "bad", "amazon.com")
    assert resolution.path == ResolutionPath.FAIL


def test_lifecycle_promotion_thresholds() -> None:
    lifecycle = CapabilityLifecycle(PromotionPolicy(min_successful_runs=2, min_evaluator_score=0.7))
    assert lifecycle.can_promote(1, 0.9, 0, True) is False
    assert lifecycle.can_promote(2, 0.8, 0, True) is True


def test_memory_reuse_with_signature_and_confidence(tmp_path: Path) -> None:
    mem = CapabilityMemory(tmp_path / "mem.json")
    sig = mem.normalize_task_signature("Find latest amazon order")
    from app.capabilities.models import CapabilityUsageRecord

    mem.record(CapabilityUsageRecord(capability_id="c1", task="Find latest amazon order", task_signature=sig, success=True, evaluator_score=0.9))
    mem.record(CapabilityUsageRecord(capability_id="c1", task="Find latest amazon order", task_signature=sig, success=False, evaluator_score=0.2))
    assert len(mem.successful_for_task("find   latest amazon order")) == 1
    assert mem.confidence_for_capability("c1") > 0


def test_resolver_prefers_stable_over_generated_candidate() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    registry = CapabilityRegistry()
    stable = _cap("lookup", CapabilityStatus.STABLE, CapabilityType.STABLE, ["amazon.com"])
    candidate = _cap("lookup_candidate", CapabilityStatus.GENERATED_CANDIDATE, CapabilityType.GENERATED_CANDIDATE, ["amazon.com"])
    registry.register(stable)
    registry.register(candidate)
    result = registry.resolve_by_relevance("lookup amazon", "amazon.com")
    assert result is not None
    assert result.capability_type == CapabilityType.STABLE
