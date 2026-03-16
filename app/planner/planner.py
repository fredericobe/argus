import json
import logging
from typing import Any, Protocol

from openai import OpenAI
from pydantic import ValidationError

from app.config.settings import ArgusSettings
from app.models.planner_models import PlannerDecision
from app.planner.prompts import SYSTEM_PROMPT, build_planner_prompt

logger = logging.getLogger(__name__)


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
        last_error: Exception | None = None
        for attempt in (1, 2):
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
                decision = self._parse_and_validate(text, available_skills)
                return decision
            except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
                last_error = exc
                logger.warning(
                    "planner_malformed_response=%s",
                    json.dumps({"attempt": attempt, "error": str(exc), "raw": text}, default=str),
                )

        raise ValueError("Planner returned invalid structured output after retry") from last_error

    @staticmethod
    def _parse_and_validate(text: str, available_skills: list[str]) -> PlannerDecision:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("Planner payload must be a JSON object")

        decision = PlannerDecision.model_validate(payload)

        if decision.skill_name not in available_skills:
            raise ValueError(f"Unknown skill requested by planner: {decision.skill_name}")

        if not isinstance(decision.arguments, dict):
            raise ValueError("Planner arguments must be an object")
        for k, v in decision.arguments.items():
            if not isinstance(k, str):
                raise TypeError("Planner argument keys must be strings")
            if not isinstance(v, str):
                raise TypeError("Planner argument values must be strings")

        return decision
