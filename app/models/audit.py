from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class StepAuditRecord(BaseModel):
    step: int
    planner_decision: str
    skill_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    observation_kind: str
    observation_message: str
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
