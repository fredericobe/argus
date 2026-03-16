from app.models.observation import AgentObservation
from app.skills.base import SkillContext


class LoginAmazonSkill:
    name = "login_amazon"
    description = "Log into Amazon using credential provider values."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        username = context.credentials.get_secret("amazon", "username")
        password = context.credentials.get_secret("amazon", "password")
        if not username or not password:
            return AgentObservation(
                kind="error_occurred",
                message="Amazon credentials unavailable. Provide via keyring or environment.",
            )

        context.browser.wait_for_selector("input[name='email']")
        context.browser.type_text("input[name='email']", username)
        context.browser.click("input#continue")
        context.browser.wait_for_selector("input[name='password']")
        context.browser.type_text("input[name='password']", password)
        context.browser.click("input#signInSubmit")
        return AgentObservation(kind="skill_completed", message="Attempted Amazon login")


class OpenOrdersPageSkill:
    name = "open_orders_page"
    description = "Open Amazon order history page."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        url = "https://www.amazon.com/gp/your-account/order-history"
        context.browser.open_url(url)
        return AgentObservation(kind="page_loaded", message="Opened Amazon orders page", data={"url": url})


class GetLatestOrderSkill:
    name = "get_latest_order"
    description = "Locate latest Amazon order container."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        selector = arguments.get("selector", "div.order")
        context.browser.wait_for_selector(selector)
        return AgentObservation(
            kind="element_found",
            message="Latest order container located",
            data={"selector": selector},
        )


class ExtractOrderStatusSkill:
    name = "extract_order_status"
    description = "Extract delivery status text from latest Amazon order."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        selector = arguments.get("selector", "div.order span.a-color-success")
        text = context.browser.extract_text(selector)
        return AgentObservation(
            kind="text_extracted",
            message="Extracted latest order status",
            data={"selector": selector, "status": text},
        )
