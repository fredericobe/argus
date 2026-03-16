import pytest

from app.capabilities.models import (
    Capability,
    CapabilityStatus,
    CapabilityType,
    ImplementationKind,
    RiskLevel,
)
from app.capabilities.registry import CapabilityRegistry


def _cap(name: str, cid: str, capability_type: CapabilityType = CapabilityType.STABLE) -> Capability:
    return Capability(
        id=cid,
        name=name,
        description=f"capability {name}",
        status=CapabilityStatus.STABLE,
        capability_type=capability_type,
        implementation_kind=ImplementationKind.SKILL,
        implementation_ref=name,
        allowed_domains=["amazon.com"],
        risk_level=RiskLevel.LOW,
    )


def test_register_and_list_by_type_and_name() -> None:
    registry = CapabilityRegistry()
    registry.register(_cap("stable_cap", "1", CapabilityType.STABLE))
    registry.register(_cap("learned_cap", "2", CapabilityType.LEARNED))
    registry.register(_cap("generated_cap", "3", CapabilityType.GENERATED_TEMPORARY))

    assert registry.resolve_by_name("stable_cap") is not None
    learned = registry.list_capabilities(capability_type=CapabilityType.LEARNED)
    assert [cap.name for cap in learned] == ["learned_cap"]


def test_resolve_by_domain_and_duplicate_registration_and_usage_preference() -> None:
    registry = CapabilityRegistry()
    cap = _cap("orders", "1")
    registry.register(cap)

    with pytest.raises(ValueError):
        registry.register(_cap("orders", "2"))

    assert registry.list_capabilities(domain="amazon.com")
    registry.mark_usage("1")
    assert registry.resolve_by_relevance("orders status", domain="amazon.com") is not None
