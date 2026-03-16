from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.builder.code_provider import CodeGenerationProvider
from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxRunner
from app.builder.spec import CapabilitySpec
from app.capabilities.artifacts import CapabilityArtifactStore
from app.capabilities.audit import CapabilityAuditLogger
from app.capabilities.lifecycle import CapabilityLifecycle
from app.capabilities.models import Capability, CapabilityStatus, CapabilityType, ImplementationKind


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
        artifact_store: CapabilityArtifactStore | None = None,
        audit_logger: CapabilityAuditLogger | None = None,
    ) -> None:
        self.code_provider = code_provider
        self.sandbox = sandbox
        self.evaluator = evaluator
        self.lifecycle = lifecycle
        self.artifact_store = artifact_store
        self.audit_logger = audit_logger or CapabilityAuditLogger()

    def create_spec(self, task: str, name: str, allowed_domains: list[str]) -> CapabilitySpec:
        minimal_domains = sorted(set(allowed_domains))[:3]
        return CapabilitySpec(
            name=name,
            task=task,
            description=f"Generated capability for: {task}",
            allowed_domains=minimal_domains,
            required_inputs=["task"],
            expected_outputs=["data", "evidence"],
        )

    def build(self, task: str, name: str, allowed_domains: list[str]) -> BuildResult:
        spec = self.create_spec(task=task, name=name, allowed_domains=allowed_domains)
        self.audit_logger.log_event("spec_created", name, task, spec.allowed_domains, "spec initialized")
        package = self.code_provider.generate(spec)
        self.audit_logger.log_event("generation_completed", package.capability_id, task, spec.allowed_domains, "code generated")

        capability_id = package.capability_id or f"generated-{uuid4()}"
        capability = Capability(
            id=capability_id,
            name=spec.name,
            description=spec.description,
            version=package.version,
            status=CapabilityStatus.GENERATED_TEMPORARY,
            capability_type=CapabilityType.GENERATED_TEMPORARY,
            implementation_kind=ImplementationKind.GENERATED_CODE,
            allowed_domains=package.declared_domains,
            required_inputs=spec.required_inputs,
            expected_outputs=spec.expected_outputs,
            implementation_ref=package.entrypoint,
            author="argus-builder",
            source="generated",
            metadata={"manifest": package.metadata, "source_code": package.source_code},
        )

        validation = self.sandbox.validate_package(package)
        self.audit_logger.log_event("package_validated", capability.id, task, capability.allowed_domains, validation.reason or "validated")
        if not validation.passed:
            rejected = self.lifecycle.reject(capability, validation.reason)
            result = BuildResult(
                capability=rejected,
                artifacts=BuildArtifacts(
                    spec=spec,
                    source_code=package.source_code,
                    validation_result=validation.output | {"reason": validation.reason, "passed": False},
                    evaluation_result={"accepted": False, "reason": validation.reason, "score": 0.0},
                ),
            )
            self._persist(result)
            return result

        sandbox_result = self.sandbox.execute(package, {"task": task})
        self.audit_logger.log_event("sandbox_executed", capability.id, task, capability.allowed_domains, sandbox_result.reason or "sandbox ok")
        evaluation = self.evaluator.evaluate(capability, sandbox_result)
        self.audit_logger.log_event("evaluation_completed", capability.id, task, capability.allowed_domains, evaluation.reason)
        if evaluation.accepted:
            capability = self.lifecycle.mark_candidate(capability)
        else:
            capability = self.lifecycle.reject(capability, evaluation.reason)

        result = BuildResult(
            capability=capability,
            artifacts=BuildArtifacts(
                spec=spec,
                source_code=package.source_code,
                validation_result=validation.output | {"passed": validation.passed},
                evaluation_result={
                    "accepted": evaluation.accepted,
                    "promotable": evaluation.promotable,
                    "reason": evaluation.reason,
                    "score": evaluation.score,
                    "evidence_quality": evaluation.evidence_quality,
                    "sandbox": sandbox_result.output,
                },
            ),
        )
        self._persist(result)
        return result

    def _persist(self, result: BuildResult) -> None:
        if not self.artifact_store:
            return
        self.artifact_store.persist(
            capability_id=result.capability.id,
            metadata=result.capability.model_dump(mode="json"),
            source_code=result.artifacts.source_code,
            sandbox_result=result.artifacts.validation_result,
            evaluation=result.artifacts.evaluation_result,
        )
