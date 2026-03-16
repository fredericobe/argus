from app.models.observation import AgentObservation
from app.models.planner_models import PlannerDecision
from app.planner.agent_runtime import AgentRuntime
from app.safety.safety_policy import SafetyPolicy
from app.skills.base import SkillContext
from app.skills.registry import SkillRegistry


class FakePlanner:
    def __init__(self) -> None:
        self.calls = 0

    def next_decision(
        self,
        user_request: str,
        last_observation: str,
        step: int,
        available_skills: list[str],
    ) -> PlannerDecision:
        self.calls += 1
        if self.calls == 1:
            return PlannerDecision(skill_name="navigate_to_url", arguments={"url": "https://www.amazon.com"})
        return PlannerDecision(skill_name="finish", is_complete=True, final_response="done")


class FakeCredentialProvider:
    def get_secret(self, service: str, key: str) -> str | None:
        return None


class NavigateSkill:
    name = "navigate_to_url"
    description = "navigate"

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        return AgentObservation(kind="navigation_complete", message=f"Opened {arguments['url']}")


def test_agent_runtime_finishes_and_records_audit() -> None:
    runtime = AgentRuntime(
        planner=FakePlanner(),
        skill_registry=SkillRegistry([NavigateSkill()]),
        skill_context=SkillContext(browser=None, credentials=FakeCredentialProvider()),  # type: ignore[arg-type]
        safety_policy=SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=5),
    )

    final_observation, audit = runtime.run("check order", initial_observation="start")

    assert final_observation.kind == "task_finished"
    assert final_observation.message == "done"
    assert len(audit) == 2
    assert audit[0].skill_name == "navigate_to_url"


class BrokenPlanner:
    def next_decision(
        self,
        user_request: str,
        last_observation: str,
        step: int,
        available_skills: list[str],
    ) -> PlannerDecision:
        _ = (user_request, last_observation, step, available_skills)
        raise ValueError("malformed planner output")


def test_agent_runtime_returns_structured_planner_failure() -> None:
    runtime = AgentRuntime(
        planner=BrokenPlanner(),
        skill_registry=SkillRegistry([NavigateSkill()]),
        skill_context=SkillContext(browser=None, credentials=FakeCredentialProvider()),  # type: ignore[arg-type]
        safety_policy=SafetyPolicy(allowed_domains=["amazon.com"], blocked_domains=[], max_steps=5),
    )

    final_observation, audit = runtime.run("check order", initial_observation="start")

    assert final_observation.kind == "error_occurred"
    assert "Planner failed" in final_observation.message
    assert audit[0].skill_name == "planner"
