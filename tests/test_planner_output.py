import json
from types import SimpleNamespace

import pytest

from app.config.settings import ArgusSettings
from app.planner.planner import LLMPlanner, PlannerOutputError


class FakeResponses:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls = 0

    def create(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        out = self.outputs[self.calls]
        self.calls += 1
        return SimpleNamespace(output_text=out)


class FakeClient:
    def __init__(self, outputs: list[str]) -> None:
        self.responses = FakeResponses(outputs)


def _settings() -> ArgusSettings:
    return ArgusSettings(ARGUS_OPENAI_API_KEY="test")


def test_parse_and_validate_enforces_skill_and_argument_types() -> None:
    decision = LLMPlanner._parse_and_validate(
        '{"skill":"navigate_to_url","arguments":{"url":"https://www.amazon.com"},"reasoning":"go","done":false}',
        ["navigate_to_url", "finish"],
    )
    assert decision.skill_name == "navigate_to_url"

    with pytest.raises(ValueError):
        LLMPlanner._parse_and_validate(
            '{"skill":"unknown","arguments":{},"reasoning":"go","done":false}',
            ["navigate_to_url", "finish"],
        )

    with pytest.raises(ValueError):
        LLMPlanner._parse_and_validate(
            '{"skill":"navigate_to_url","arguments":"not-an-object","reasoning":"go","done":false}',
            ["navigate_to_url", "finish"],
        )


def test_next_decision_retries_once_for_malformed_output() -> None:
    planner = LLMPlanner(_settings())
    planner.client = FakeClient(
        outputs=[
            "not-json",
            '{"skill":"finish","arguments":{},"reasoning":"done","done":true}',
        ]
    )

    decision = planner.next_decision(
        user_request="test",
        last_observation="start",
        step=1,
        available_skills=["navigate_to_url", "finish"],
    )
    assert decision.skill_name == "finish"
    assert planner.client.responses.calls == 2


def test_next_decision_fails_after_retry() -> None:
    planner = LLMPlanner(_settings())
    planner.client = FakeClient(outputs=["not-json", "still-not-json"])

    with pytest.raises(PlannerOutputError):
        planner.next_decision(
            user_request="test",
            last_observation="start",
            step=1,
            available_skills=["navigate_to_url", "finish"],
        )


def test_parse_and_validate_rejects_malformed_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        LLMPlanner._parse_and_validate("{", ["navigate_to_url", "finish"])
