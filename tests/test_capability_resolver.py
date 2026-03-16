from app.capabilities.models import (
    Capability,
    CapabilityStatus,
    CapabilityType,
    ImplementationKind,
    RiskLevel,
)
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.resolver import CapabilityResolver, ResolutionPath
from app.safety.safety_policy import SafetyPolicy


def _cap(name: str, cid: str, ctype: CapabilityType, risk: RiskLevel = RiskLevel.LOW, domains: list[str] | None = None) -> Capability:
    return Capability(
        id=cid,
        name=name,
        description=f"{name} description",
        status=CapabilityStatus.STABLE,
        capability_type=ctype,
        implementation_kind=ImplementationKind.SKILL,
        implementation_ref=name,
        allowed_domains=domains or ["amazon.com"],
        risk_level=risk,
    )


def test_resolver_prefers_stable_then_learned_then_generation() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=5)
    registry = CapabilityRegistry()
    stable = _cap("navigate_to_url", "s1", CapabilityType.STABLE)
    learned = _cap("order_lookup", "l1", CapabilityType.LEARNED)
    registry.register(stable)
    registry.register(learned)
    resolver = CapabilityResolver(registry, policy)

    stable_result = resolver.resolve("navigate", "navigate_to_url")
    assert stable_result.path == ResolutionPath.STABLE

    learned_result = resolver.resolve("lookup order", "missing")
    assert learned_result.path == ResolutionPath.LEARNED

    generated_result = resolver.resolve("unseen thing", "no_match")
    assert generated_result.path == ResolutionPath.GENERATED


def test_resolver_blocks_unsafe_and_requires_confirmation_for_high_risk() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=["blocked.com"], max_steps=5)
    registry = CapabilityRegistry()
    registry.register(_cap("danger", "h1", CapabilityType.LEARNED, risk=RiskLevel.HIGH))
    registry.register(_cap("blocked", "b1", CapabilityType.LEARNED, domains=["blocked.com"]))

    resolver = CapabilityResolver(registry, policy)
    assert resolver.resolve("danger", "danger").path == ResolutionPath.HUMAN_CONFIRMATION
    assert resolver.resolve("blocked", "blocked").path == ResolutionPath.FAIL
