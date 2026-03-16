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
from app.skills.registry import SkillRegistry, stable_capabilities_from_skills


class FakePlannerStable:
    def __init__(self) -> None:
        self.calls = 0

    def next_decision(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return PlannerDecision(skill_name="navigate_to_url", arguments={"url": "https://amazon.com"})
        return PlannerDecision(skill_name="finish", is_complete=True, final_response="done")


class FakePlannerGenerated:
    def __init__(self) -> None:
        self.calls = 0

    def next_decision(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return PlannerDecision(skill_name="unknown_skill", arguments={"domain": "amazon.com"})
        return PlannerDecision(skill_name="finish", is_complete=True, final_response="done")


class FakeCredentialProvider:
    def get_secret(self, service: str, key: str):
        return None


class NavigateSkill:
    name = "navigate_to_url"
    description = "navigate"

    def execute(self, arguments, context):
        from app.models.observation import AgentObservation

        return AgentObservation(kind="navigation_complete", message=f"Opened {arguments['url']}")


def _runtime(planner, tmp_path: Path, generated_enabled: bool) -> AgentRuntime:
    policy = SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=4)
    skills = [NavigateSkill()]
    skill_registry = SkillRegistry(skills)
    capability_registry = CapabilityRegistry()
    for cap in stable_capabilities_from_skills(skills):
        capability_registry.register(cap)
    resolver = CapabilityResolver(capability_registry, policy)
    builder = CapabilityBuilder(
        code_provider=StubCodeGenerationProvider(),
        sandbox=SandboxRunner(enabled=True, timeout_seconds=2),
        evaluator=CapabilityEvaluator(policy),
        lifecycle=CapabilityLifecycle(),
    )
    memory = CapabilityMemory(tmp_path / "cap_memory.json")
    return AgentRuntime(
        planner=planner,
        skill_registry=skill_registry,
        skill_context=SkillContext(browser=None, credentials=FakeCredentialProvider()),  # type: ignore[arg-type]
        safety_policy=policy,
        capability_registry=capability_registry,
        capability_resolver=resolver,
        capability_builder=builder,
        capability_memory=memory,
        enable_generated_capabilities=generated_enabled,
    )


def test_planner_uses_stable_capability_when_available(tmp_path: Path) -> None:
    runtime = _runtime(FakePlannerStable(), tmp_path, generated_enabled=False)
    final_obs, audit = runtime.run("check order", "start")
    assert final_obs.kind == "task_finished"
    assert audit[0].skill_name == "navigate_to_url"


def test_generated_path_returns_structured_observation_and_no_crash(tmp_path: Path) -> None:
    runtime = _runtime(FakePlannerGenerated(), tmp_path, generated_enabled=True)
    final_obs, audit = runtime.run("do new thing", "start")
    assert final_obs.kind == "task_finished"
    assert audit[0].observation_kind in {"skill_completed", "error_occurred"}
