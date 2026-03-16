from app.models.observation import AgentObservation
from app.skills.base import SkillContext


class NavigateToUrlSkill:
    name = "navigate_to_url"
    description = "Navigate browser to a URL within allowed domains."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        url = arguments.get("url", "")
        if not url:
            return AgentObservation(kind="error_occurred", message="Missing required argument: url")
        try:
            opened = context.browser.open_url(url)
            return AgentObservation(kind="navigation_complete", message=f"Opened {opened}", data={"url": opened})
        except RuntimeError as exc:
            return AgentObservation(kind="error_occurred", message=f"Navigation failed: {exc}", data={"url": url})


class ExtractTextFromPageSkill:
    name = "extract_text_from_page"
    description = "Extract text from current page using a CSS selector."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        selector = arguments.get("selector", "")
        if not selector:
            return AgentObservation(kind="error_occurred", message="Missing required argument: selector")
        try:
            value = context.browser.extract_text(selector)
            return AgentObservation(
                kind="text_extracted",
                message=f"Extracted text from {selector}",
                data={"selector": selector, "text": value},
            )
        except RuntimeError as exc:
            return AgentObservation(
                kind="error_occurred",
                message=f"Text extraction failed for {selector}: {exc}",
                data={"selector": selector},
            )
