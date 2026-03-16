from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.builder.code_provider import CodeGenerationProvider
from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxRunner
from app.builder.spec import CapabilitySpec
from app.capabilities.lifecycle import CapabilityLifecycle
from app.capabilities.models import (
    Capability,
    CapabilityStatus,
    CapabilityType,
    ImplementationKind,
)


@dataclass(slots=True)
class BuildArtifacts:
    spec: CapabilitySpec
    source_code: str
    validation_result: dict[str, object]
    evaluation_result: dict[str, object]


@dataclass(slots=True)
class BuildResult:
    capability: Capability
    artifacts: BuildArtifacts


class CapabilityBuilder:
    def __init__(
        self,
        code_provider: CodeGenerationProvider,
        sandbox: SandboxRunner,
        evaluator: CapabilityEvaluator,
        lifecycle: CapabilityLifecycle,
    ) -> None:
        self.code_provider = code_provider
        self.sandbox = sandbox
        self.evaluator = evaluator
        self.lifecycle = lifecycle

    def create_spec(self, task: str, name: str, allowed_domains: list[str]) -> CapabilitySpec:
        return CapabilitySpec(
            name=name,
            task=task,
            description=f"Generated capability for: {task}",
            allowed_domains=allowed_domains,
            required_inputs=["task"],
            expected_outputs=["summary", "evidence"],
        )

    def build(self, task: str, name: str, allowed_domains: list[str]) -> BuildResult:
        spec = self.create_spec(task=task, name=name, allowed_domains=allowed_domains)
        package = self.code_provider.generate(spec)

        capability = Capability(
            id=f"generated-{uuid4()}",
            name=spec.name,
            description=spec.description,
            status=CapabilityStatus.GENERATED_TEMPORARY,
            capability_type=CapabilityType.GENERATED_TEMPORARY,
            implementation_kind=ImplementationKind.GENERATED_CODE,
            allowed_domains=spec.allowed_domains,
            required_inputs=spec.required_inputs,
            expected_outputs=spec.expected_outputs,
            implementation_ref=package.entrypoint,
            author="argus-builder",
            source="generated",
            metadata={"manifest": package.manifest},
        )

        validation = self.sandbox.validate_package(package)
        if not validation.passed:
            rejected = self.lifecycle.reject(capability, validation.reason)
            return BuildResult(
                capability=rejected,
                artifacts=BuildArtifacts(
                    spec=spec,
                    source_code=package.source_code,
                    validation_result=validation.output | {"reason": validation.reason, "passed": False},
                    evaluation_result={"accepted": False, "reason": validation.reason},
                ),
            )

        sandbox_result = self.sandbox.execute(package, {"task": task})
        evaluation = self.evaluator.evaluate(capability, sandbox_result)
        if evaluation.accepted:
            capability = self.lifecycle.mark_candidate(capability)
        else:
            capability = self.lifecycle.reject(capability, evaluation.reason)

        return BuildResult(
            capability=capability,
            artifacts=BuildArtifacts(
                spec=spec,
                source_code=package.source_code,
                validation_result=validation.output | {"passed": validation.passed},
                evaluation_result={
                    "accepted": evaluation.accepted,
                    "promotable": evaluation.promotable,
                    "reason": evaluation.reason,
                    "sandbox": sandbox_result.output,
                },
            ),
        )
