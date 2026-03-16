from collections.abc import Callable
import json
import logging

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
        confirmation_hook: Callable[[PlannerDecision], bool] | None = None,
    ) -> None:
        self.planner = planner
        self.skill_registry = skill_registry
        self.skill_context = skill_context
        self.safety_policy = safety_policy
        self.confirmation_hook = confirmation_hook or (lambda _d: False)

    def run(self, user_request: str, initial_observation: str) -> tuple[AgentObservation, list[StepAuditRecord]]:
        last_observation = AgentObservation(kind="skill_completed", message=initial_observation)
        audit_records: list[StepAuditRecord] = []

        for step in range(1, self.safety_policy.max_steps + 1):
            self.safety_policy.check_step_limit(step)
            decision = self.planner.next_decision(
                user_request=user_request,
                last_observation=last_observation.message,
                step=step,
                available_skills=self.skill_registry.names() + ["finish"],
            )

            if decision.is_complete or decision.skill_name == "finish":
                final_obs = AgentObservation(
                    kind="task_finished",
                    message=decision.final_response or "Task complete",
                )
                audit_records.append(
                    StepAuditRecord(
                        step=step,
                        planner_decision=decision.rationale,
                        skill_name="finish",
                        arguments={},
                        observation_kind=final_obs.kind,
                        observation_message=final_obs.message,
                    )
                )
                return final_obs, audit_records

            self.safety_policy.validate_skill(decision.skill_name, decision.arguments)
            if self.safety_policy.requires_confirmation_for_skill(decision.skill_name, decision.arguments):
                if not self.confirmation_hook(decision):
                    raise RuntimeError("Destructive skill requested without explicit confirmation")

            try:
                observation = self.skill_registry.execute(decision.skill_name, decision.arguments, self.skill_context)
                error = None
            except Exception as exc:  # noqa: BLE001
                observation = AgentObservation(kind="error_occurred", message=f"Skill execution failed: {exc}")
                error = str(exc)

            audit = StepAuditRecord(
                step=step,
                planner_decision=decision.rationale,
                skill_name=decision.skill_name,
                arguments=decision.arguments,
                observation_kind=observation.kind,
                observation_message=observation.message,
                error=error,
            )
            audit_records.append(audit)
            logger.info("agent_step=%s", json.dumps(audit.model_dump(mode="json"), default=str))
            last_observation = observation

        final_obs = AgentObservation(kind="task_finished", message="Stopped due to max step limit")
        return final_obs, audit_records
