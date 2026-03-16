from typing import Literal

from pydantic import BaseModel, Field


ActionType = Literal[
    "open_url",
    "click",
    "type_text",
    "extract_text",
    "wait_for_selector",
    "take_screenshot",
    "save_session",
    "finish",
]


class AgentAction(BaseModel):
    action: ActionType
    url: str | None = None
    selector: str | None = None
    text: str | None = None
    description: str = Field(default="")


class AgentStepResult(BaseModel):
    step: int
    action: AgentAction
    observation: str
    success: bool = True
