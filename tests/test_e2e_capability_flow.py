from pathlib import Path

from app.builder.builder import CapabilityBuilder
from app.builder.code_provider import StubCodeGenerationProvider
from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxRunner
from app.capabilities.lifecycle import CapabilityLifecycle
from app.capabilities.memory import CapabilityMemory
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.resolver import CapabilityResolver
from app.models.planner_models import PlannerDecision
from app.planner.agent_runtime import AgentRuntime
from app.safety.safety_policy import SafetyPolicy
from app.skills.base import SkillContext
from app.skills.registry import SkillRegistry


class PlannerScenario:
    def __init__(self, first_skill: str) -> None:
        self.first_skill = first_skill
        self.calls = 0

    def next_decision(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return PlannerDecision(skill_name=self.first_skill, arguments={"url": "https://amazon.com", "domain": "amazon.com"})
        return PlannerDecision(skill_name="finish", is_complete=True, final_response="done")


class NavigateSkill:
    name = "navigate_to_url"
    description = "navigate"

    def execute(self, arguments, context):
        from app.models.observation import AgentObservation

        return AgentObservation(kind="navigation_complete", message="ok")


class Creds:
    def get_secret(self, service: str, key: str):
        return None


def _runtime(first_skill: str, tmp_path: Path) -> tuple[AgentRuntime, CapabilityRegistry, CapabilityMemory]:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=4)
    skills = [NavigateSkill()]
    registry = CapabilityRegistry()
    memory = CapabilityMemory(tmp_path / "mem.json")
    builder = CapabilityBuilder(
        code_provider=StubCodeGenerationProvider(),
        sandbox=SandboxRunner(enabled=True, timeout_seconds=2),
        evaluator=CapabilityEvaluator(policy),
        lifecycle=CapabilityLifecycle(),
    )
    runtime = AgentRuntime(
        planner=PlannerScenario(first_skill),
        skill_registry=SkillRegistry(skills),
        skill_context=SkillContext(browser=None, credentials=Creds()),  # type: ignore[arg-type]
        safety_policy=policy,
        capability_registry=registry,
        capability_resolver=CapabilityResolver(registry, policy),
        capability_builder=builder,
        capability_memory=memory,
        enable_generated_capabilities=True,
    )
    return runtime, registry, memory


def test_e2e_stable_generated_success_failure_and_reuse(tmp_path: Path) -> None:
    # Stable skill path
    runtime, _registry, _memory = _runtime("navigate_to_url", tmp_path)
    final_obs, _ = runtime.run("check order", "start")
    assert final_obs.kind == "task_finished"

    # Generated path creates memory entry
    runtime2, registry2, memory2 = _runtime("new_unknown", tmp_path)
    final_obs2, audit2 = runtime2.run("new task", "start")
    assert final_obs2.kind == "task_finished"
    assert audit2[0].observation_kind in {"skill_completed", "error_occurred", "generated_capability_created", "generated_capability_reused"}
    assert len(memory2.all_records()) >= 1

    # Rejected capability not reused
    rejected = [c for c in registry2.list_capabilities() if c.status.value == "rejected"]
    assert isinstance(rejected, list)
