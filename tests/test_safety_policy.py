import pytest

from app.safety.safety_policy import SafetyPolicy, SafetyViolationError


def test_allows_whitelisted_domain_and_subdomain() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    policy.validate_skill("navigate_to_url", {"url": "https://amazon.com"})
    policy.validate_skill("navigate_to_url", {"url": "https://www.amazon.com/gp/your-account/order-history"})
    policy.validate_skill("navigate_to_url", {"url": "https://orders.amazon.com/latest"})
    policy.validate_skill("navigate_to_url", {"url": "https://amazon.com:443/"})


def test_blocks_non_whitelisted_domain() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    with pytest.raises(SafetyViolationError):
        policy.validate_skill("navigate_to_url", {"url": "https://example.org"})


def test_blocks_evil_substring_domains() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    with pytest.raises(SafetyViolationError):
        policy.validate_skill("navigate_to_url", {"url": "https://evilamazon.com"})
    with pytest.raises(SafetyViolationError):
        policy.validate_skill("navigate_to_url", {"url": "https://amazon.com.evil.com"})
    with pytest.raises(SafetyViolationError):
        policy.validate_skill("navigate_to_url", {"url": "https://login-amazon.com"})


def test_blocks_blocked_domain_even_if_allowed() -> None:
    policy = SafetyPolicy(
        allowed_domains=["amazon.com", "paypal.com"],
        blocked_domains=["paypal.com"],
        max_steps=3,
    )
    with pytest.raises(SafetyViolationError):
        policy.validate_skill("navigate_to_url", {"url": "https://www.paypal.com/home"})


def test_rejects_missing_url_for_navigate() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    with pytest.raises(SafetyViolationError):
        policy.validate_skill("navigate_to_url", {})


def test_destructive_skill_requires_confirmation() -> None:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=3)
    assert policy.requires_confirmation_for_skill("submit_payment", {}) is True
