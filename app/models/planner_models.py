from pydantic import BaseModel, Field


class PlannerDecision(BaseModel):
    skill_name: str
    arguments: dict[str, str] = Field(default_factory=dict)
    rationale: str = ""
    is_complete: bool = False
    final_response: str | None = None
