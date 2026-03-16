from app.models.observation import AgentObservation
from app.skills.amazon import ExtractOrderStatusSkill
from app.skills.base import SkillContext
from app.skills.common import ExtractTextFromPageSkill, NavigateToUrlSkill


class FakeBrowser:
    def __init__(self) -> None:
        self.url = ""

    def open_url(self, url: str) -> str:
        self.url = url
        return url

    def extract_text(self, selector: str) -> str:
        if selector == ".missing":
            raise RuntimeError("not found")
        return "hello"

    def selector_exists(self, selector: str) -> bool:
        return selector != ".missing"


class FakeCredentials:
    def get_secret(self, service: str, key: str) -> str | None:
        _ = (service, key)
        return None


def _ctx(browser: FakeBrowser | None = None) -> SkillContext:
    return SkillContext(browser=browser or FakeBrowser(), credentials=FakeCredentials())  # type: ignore[arg-type]


def test_navigate_skill_validates_required_args() -> None:
    obs = NavigateToUrlSkill().execute({}, _ctx())
    assert isinstance(obs, AgentObservation)
    assert obs.kind == "error_occurred"


def test_extract_text_skill_validates_required_args() -> None:
    obs = ExtractTextFromPageSkill().execute({}, _ctx())
    assert obs.kind == "error_occurred"


def test_extract_order_status_returns_structured_failure_when_missing() -> None:
    obs = ExtractOrderStatusSkill().execute({"selector": ".missing"}, _ctx())
    assert obs.kind == "error_occurred"
    assert obs.data["reason"] in {"element_missing", "extraction_failed"}
