from app.skills.amazon import (
    ExtractOrderStatusSkill,
    GetLatestOrderSkill,
    LoginAmazonSkill,
    OpenOrdersPageSkill,
)
from app.skills.base import Skill, SkillContext
from app.skills.common import ExtractTextFromPageSkill, NavigateToUrlSkill


class SkillRegistry:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = {skill.name: skill for skill in skills}

    def get(self, name: str) -> Skill:
        if name not in self._skills:
            raise KeyError(f"Unknown skill: {name}")
        return self._skills[name]

    def names(self) -> list[str]:
        return sorted(self._skills.keys())

    def execute(self, name: str, arguments: dict[str, str], context: SkillContext):
        return self.get(name).execute(arguments, context)


DEFAULT_SKILLS: list[Skill] = [
    NavigateToUrlSkill(),
    ExtractTextFromPageSkill(),
    LoginAmazonSkill(),
    OpenOrdersPageSkill(),
    GetLatestOrderSkill(),
    ExtractOrderStatusSkill(),
]
