from app.builder.builder import CapabilityBuilder
from app.builder.code_provider import GeneratedCapabilityPackage
from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxRunner
from app.capabilities.lifecycle import CapabilityLifecycle
from app.safety.safety_policy import SafetyPolicy


class FailingProvider:
    def generate(self, spec):
        raise RuntimeError("provider failure")


class GoodProvider:
    def generate(self, spec):
        return GeneratedCapabilityPackage(
            source_code="def run(arguments):\n    return {'status':'ok','evidence':['ok']}\n",
            entrypoint="run",
            manifest={"name": spec.name},
        )


class BadProvider:
    def generate(self, spec):
        return GeneratedCapabilityPackage(
            source_code="def nope():\n    return {}\n",
            entrypoint="nope",
            manifest={"name": spec.name},
        )


def _builder(provider) -> CapabilityBuilder:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=5)
    return CapabilityBuilder(
        code_provider=provider,
        sandbox=SandboxRunner(enabled=True, timeout_seconds=5),
        evaluator=CapabilityEvaluator(policy),
        lifecycle=CapabilityLifecycle(),
    )


def test_builder_creates_spec_calls_provider_and_emits_artifacts() -> None:
    builder = _builder(GoodProvider())
    result = builder.build("check order", "generated_check_order", ["amazon.com"])
    assert result.capability.name == "generated_check_order"
    assert result.artifacts.spec.task == "check order"
    assert result.artifacts.validation_result["passed"] is True


def test_builder_handles_provider_failure_safely() -> None:
    builder = _builder(FailingProvider())
    try:
        builder.build("check order", "generated_check_order", ["amazon.com"])
    except RuntimeError as exc:
        assert "provider failure" in str(exc)


def test_builder_rejects_malformed_package() -> None:
    builder = _builder(BadProvider())
    result = builder.build("check order", "generated_check_order", ["amazon.com"])
    assert result.capability.status.value == "rejected"
