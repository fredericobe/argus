import json
from typing import Protocol

from openai import OpenAI

from app.config.settings import ArgusSettings
from app.models.planner_models import PlannerDecision
from app.planner.prompts import SYSTEM_PROMPT, build_planner_prompt


class Planner(Protocol):
    def next_decision(
        self,
        user_request: str,
        last_observation: str,
        step: int,
        available_skills: list[str],
    ) -> PlannerDecision: ...


class LLMPlanner:
    def __init__(self, settings: ArgusSettings) -> None:
        if settings.model_provider.lower() != "openai":
            raise ValueError(f"Unsupported model provider: {settings.model_provider}")
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    def next_decision(
        self,
        user_request: str,
        last_observation: str,
        step: int,
        available_skills: list[str],
    ) -> PlannerDecision:
        response = self.client.responses.create(
            model=self.settings.model_name,
            temperature=self.settings.model_temperature,
            max_output_tokens=self.settings.model_max_tokens,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_planner_prompt(
                        user_request=user_request,
                        last_observation=last_observation,
                        step=step,
                        max_steps=self.settings.max_agent_steps,
                        available_skills=available_skills,
                    ),
                },
            ],
        )
        text = response.output_text.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Planner returned invalid JSON: {text}") from exc

        return PlannerDecision.model_validate(payload)
