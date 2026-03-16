from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

ObservationType = Literal[
    "page_loaded",
    "text_extracted",
    "element_found",
    "navigation_complete",
    "skill_completed",
    "error_occurred",
    "task_finished",
]


class AgentObservation(BaseModel):
    kind: ObservationType
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
