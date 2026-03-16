from typing import Any

from pydantic import BaseModel, Field, model_validator


class PlannerDecision(BaseModel):
    skill_name: str = Field(alias="skill")
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(default="", alias="reasoning")
    is_complete: bool = Field(default=False, alias="done")
    final_response: str | None = None

    @model_validator(mode="after")
    def _validate_finish_payload(self) -> "PlannerDecision":
        if self.is_complete and self.final_response is None:
            self.final_response = self.rationale or "Task complete"
        return self
