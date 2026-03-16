from __future__ import annotations

from collections.abc import Callable
import json
import logging

from app.builder.builder import CapabilityBuilder
from app.builder.code_provider import GeneratedCapabilityPackage
from app.builder.sandbox import SandboxRunner
from app.capabilities.artifacts import CapabilityArtifactStore
from app.capabilities.audit import CapabilityAuditLogger
from app.capabilities.memory import CapabilityMemory
from app.capabilities.models import Capability, CapabilityStatus, CapabilityType, CapabilityUsageRecord, ImplementationKind
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.resolver import CapabilityResolver, ResolutionPath
from app.models.audit import StepAuditRecord
from app.models.observation import AgentObservation
from app.models.planner_models import PlannerDecision
from app.safety.safety_policy import SafetyPolicy
from app.skills.base import SkillContext
from app.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(
        self,
        planner,
        skill_registry: SkillRegistry,
        skill_context: SkillContext,
        safety_policy: SafetyPolicy,
        capability_registry: CapabilityRegistry | None = None,
        capability_resolver: CapabilityResolver | None = None,
        capability_builder: CapabilityBuilder | None = None,
        capability_memory: CapabilityMemory | None = None,
        generated_sandbox: SandboxRunner | None = None,
        artifact_store: CapabilityArtifactStore | None = None,
        enable_generated_capabilities: bool = False,
        confirmation_hook: Callable[[PlannerDecision], bool] | None = None,
    ) -> None:
        self.planner = planner
        self.skill_registry = skill_registry
        self.skill_context = skill_context
        self.safety_policy = safety_policy
        self.confirmation_hook = confirmation_hook or (lambda _d: False)
        self.capability_registry = capability_registry
        self.capability_resolver = capability_resolver
        self.capability_builder = capability_builder
        self.capability_memory = capability_memory
        self.generated_sandbox = generated_sandbox or (capability_builder.sandbox if capability_builder else None)
        self.artifact_store = artifact_store
        self.enable_generated_capabilities = enable_generated_capabilities
        self.audit = CapabilityAuditLogger()

    def run(self, user_request: str, initial_observation: str) -> tuple[AgentObservation, list[StepAuditRecord]]:
        last_observation = AgentObservation(kind="skill_completed", message=initial_observation)
        audit_records: list[StepAuditRecord] = []

        for step in range(1, self.safety_policy.max_steps + 1):
            self.safety_policy.check_step_limit(step)
            try:
                decision = self.planner.next_decision(
                    user_request=user_request,
                    last_observation=last_observation.message,
                    step=step,
                    available_skills=self.skill_registry.names() + ["finish"],
                )
            except Exception as exc:  # noqa: BLE001
                observation = AgentObservation(kind="error_occurred", message=f"Planner failed: {exc}")
                audit = StepAuditRecord(step=step, planner_decision="planner_error", skill_name="planner", arguments={}, observation_kind=observation.kind, observation_message=observation.message, error=str(exc))
                audit_records.append(audit)
                self._log_trace(audit)
                return observation, audit_records

            if decision.is_complete or decision.skill_name == "finish":
                final_obs = AgentObservation(kind="task_finished", message=decision.final_response or "Task complete")
                audit = StepAuditRecord(step=step, planner_decision=decision.rationale, skill_name="finish", arguments={}, observation_kind=final_obs.kind, observation_message=final_obs.message)
                audit_records.append(audit)
                self._log_trace(audit)
                return final_obs, audit_records

            observation, error, used_capability = self._execute_decision(user_request, decision)
            audit = StepAuditRecord(step=step, planner_decision=decision.rationale, skill_name=decision.skill_name, arguments=decision.arguments, observation_kind=observation.kind, observation_message=observation.message, error=error)
            audit_records.append(audit)
            self._log_trace(audit)
            if used_capability and self.capability_memory:
                self.capability_memory.record(
                    CapabilityUsageRecord(
                        capability_id=used_capability.id,
                        task=user_request,
                        task_signature=self.capability_memory.normalize_task_signature(user_request),
                        success=observation.kind not in {"error_occurred", "generated_capability_execution_failed", "generated_capability_rejected"},
                        evaluator_score=float(used_capability.metadata.get("last_evaluator_score", 0.0)),
                        evidence_quality=float(used_capability.metadata.get("last_evidence_quality", 0.0)),
                        reason=error or observation.message,
                    )
                )
            last_observation = observation

        return AgentObservation(kind="task_finished", message="Stopped due to max step limit"), audit_records

    def _execute_decision(self, user_request: str, decision: PlannerDecision) -> tuple[AgentObservation, str | None, Capability | None]:
        try:
            if decision.skill_name in self.skill_registry.names():
                self.safety_policy.validate_skill(decision.skill_name, decision.arguments)
                if self.safety_policy.requires_confirmation_for_skill(decision.skill_name, decision.arguments) and not self.confirmation_hook(decision):
                    raise RuntimeError("Destructive skill requested without explicit confirmation")
                observation = self.skill_registry.execute(decision.skill_name, decision.arguments, self.skill_context)
                return observation, None, self._capability_for_skill(decision.skill_name)

            if not self.enable_generated_capabilities or not all([self.capability_registry, self.capability_resolver, self.capability_builder, self.generated_sandbox]):
                raise RuntimeError(f"Unknown skill requested: {decision.skill_name}")

            resolution = self.capability_resolver.resolve(task=user_request, requested_name=decision.skill_name, domain=decision.arguments.get("domain"))
            if resolution.path in {ResolutionPath.HUMAN_CONFIRMATION, ResolutionPath.FAIL}:
                raise RuntimeError(f"Capability resolution failed: {resolution.reason}")

            created = False
            if resolution.capability is None:
                build = self.capability_builder.build(task=user_request, name=f"generated_{decision.skill_name}", allowed_domains=[d for d in self.safety_policy.allowed_domains if d in (decision.arguments.get('domain') or d)])
                if build.capability.status == CapabilityStatus.REJECTED:
                    self.audit.log_event("capability_rejected", build.capability.id, user_request, build.capability.allowed_domains, str(build.capability.metadata.get("rejection_reason")))
                    return AgentObservation(kind="generated_capability_rejected", message="Generated capability rejected", data={"capability_id": build.capability.id}), str(build.capability.metadata.get("rejection_reason")), build.capability
                self.capability_registry.register(build.capability)
                self.audit.log_event("capability_registered", build.capability.id, user_request, build.capability.allowed_domains, "generated candidate registered")
                capability = build.capability
                created = True
            else:
                capability = resolution.capability

            result = self._execute_generated_capability(capability, user_request, decision.arguments)
            if not result.passed:
                self.audit.log_event("capability_executed", capability.id, user_request, capability.allowed_domains, result.reason)
                return AgentObservation(kind="generated_capability_execution_failed", message="Generated capability execution failed", data={"capability_id": capability.id, "error": result.reason}), result.reason, capability

            self.capability_registry.mark_usage(capability.id)
            self.audit.log_event("capability_executed", capability.id, user_request, capability.allowed_domains, "execution success")
            obs_kind = "generated_capability_created" if created else "generated_capability_reused"
            return AgentObservation(kind=obs_kind, message=f"Executed capability {capability.name}", data={"capability_id": capability.id, "data": result.output.get("data"), "evidence": result.output.get("evidence")}), None, capability
        except Exception as exc:  # noqa: BLE001
            logger.exception("runtime_failure skill=%s error=%s", decision.skill_name, exc)
            return AgentObservation(kind="error_occurred", message=f"Skill execution failed: {exc}", data={"skill": decision.skill_name}), str(exc), None

    def _execute_generated_capability(self, capability: Capability, request: str, arguments: dict[str, str]):
        package = GeneratedCapabilityPackage(
            capability_id=capability.id,
            version=capability.version,
            declared_domains=capability.allowed_domains,
            entrypoint=capability.implementation_ref,
            metadata=capability.metadata.get("manifest", {}),
            source_code=str(capability.metadata.get("source_code", "")),
        )
        payload = {"task": request} | arguments
        return self.generated_sandbox.execute(package, payload)

    def _capability_for_skill(self, skill_name: str) -> Capability | None:
        if not self.capability_registry:
            return None
        capability = self.capability_registry.resolve_by_name(skill_name)
        if capability:
            self.capability_registry.mark_usage(capability.id)
        return capability

    @staticmethod
    def _log_trace(audit: StepAuditRecord) -> None:
        logger.info("agent_trace=%s", json.dumps({"timestamp": audit.timestamp.isoformat(), "step": audit.step, "planner_decision": audit.planner_decision, "skill": audit.skill_name, "arguments": audit.arguments, "result": {"kind": audit.observation_kind, "message": audit.observation_message}, "error": audit.error}, default=str))
