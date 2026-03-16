from app.models.observation import AgentObservation
from app.skills.amazon import ExtractOrderStatusSkill, GetLatestOrderSkill, LoginAmazonSkill, OpenOrdersPageSkill
from app.skills.base import SkillContext
from app.skills.common import ExtractTextFromPageSkill, NavigateToUrlSkill


class FakeBrowser:
    def __init__(self) -> None:
        self.url = ""
        self.present_selectors: set[str] = set()
        self.fail_wait = False

    def open_url(self, url: str) -> str:
        self.url = url
        return url

    def current_url(self) -> str:
        return self.url

    def wait_for_selector(self, selector: str) -> None:
        if self.fail_wait:
            raise RuntimeError(f"missing {selector}")

    def extract_text(self, selector: str) -> str:
        if selector == ".missing":
            raise RuntimeError("not found")
        return "hello"

    def click(self, selector: str) -> None:
        _ = selector

    def type_text(self, selector: str, text: str) -> None:
        _ = (selector, text)

    def selector_exists(self, selector: str) -> bool:
        if selector == ".missing":
            return False
        return selector in self.present_selectors


class FakeCredentials:
    def get_secret(self, service: str, key: str) -> str | None:
        _ = (service, key)
        return None


class CompleteCredentials:
    def get_secret(self, service: str, key: str) -> str | None:
        _ = service
        return "user" if key == "username" else "pass"


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
    assert obs.data["reason"] in {"status_selector_not_found", "extraction_failed"}


def test_open_orders_page_returns_reachable_failure() -> None:
    browser = FakeBrowser()
    browser.url = "https://example.org/redirect"
    obs = OpenOrdersPageSkill().execute({}, _ctx(browser))
    assert obs.kind == "error_occurred"
    assert obs.data["reason"] == "orders_page_not_reachable"


def test_get_latest_order_returns_structured_not_found() -> None:
    browser = FakeBrowser()
    browser.fail_wait = True
    obs = GetLatestOrderSkill().execute({}, _ctx(browser))
    assert obs.kind == "error_occurred"
    assert obs.data["reason"] == "latest_order_not_found"


def test_login_amazon_reports_not_completed_when_form_still_present() -> None:
    browser = FakeBrowser()
    browser.present_selectors = {"input[name='password']", "#ap_password"}
    context = SkillContext(browser=browser, credentials=CompleteCredentials())  # type: ignore[arg-type]
    obs = LoginAmazonSkill().execute({}, context)
    assert obs.kind == "error_occurred"
    assert obs.data["reason"] == "login_not_completed"
