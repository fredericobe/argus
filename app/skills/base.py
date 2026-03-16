from dataclasses import dataclass
from typing import Protocol

from app.credentials.credential_provider import CredentialProvider
from app.executors.browser_executor import BrowserExecutor
from app.models.observation import AgentObservation


@dataclass(slots=True)
class SkillContext:
    browser: BrowserExecutor
    credentials: CredentialProvider


class Skill(Protocol):
    name: str
    description: str

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation: ...
