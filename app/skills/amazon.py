from app.models.observation import AgentObservation
from app.skills.amazon_selectors import AMAZON_SELECTORS
from app.skills.base import SkillContext


def _resolve_selector(context: SkillContext, selector_name: str, override: str | None = None) -> str:
    if override:
        return override

    selector_set = AMAZON_SELECTORS[selector_name]
    for selector in selector_set.all():
        if context.browser.selector_exists(selector):
            return selector
    return selector_set.primary


def _missing_observation(message: str, reason: str, **data: str) -> AgentObservation:
    return AgentObservation(kind="error_occurred", message=message, data={"reason": reason, **data})


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
                data={"service": "amazon", "missing": ["username", "password"]},
            )

        try:
            email_sel = _resolve_selector(context, "login_email")
            continue_sel = _resolve_selector(context, "login_continue")
            password_sel = _resolve_selector(context, "login_password")
            submit_sel = _resolve_selector(context, "login_submit")

            context.browser.wait_for_selector(email_sel)
            context.browser.type_text(email_sel, username)
            context.browser.click(continue_sel)
            context.browser.wait_for_selector(password_sel)
            context.browser.type_text(password_sel, password)
            context.browser.click(submit_sel)

            # Amazon can show extra auth challenges (CAPTCHA/MFA), so this only
            # validates that the sign-in form disappeared, not that the account is fully authenticated.
            if context.browser.selector_exists(password_sel):
                return _missing_observation(
                    "Amazon login not completed; sign-in form is still present",
                    reason="login_not_completed",
                    selector=password_sel,
                )

            return AgentObservation(kind="skill_completed", message="Attempted Amazon login")
        except RuntimeError as exc:
            return AgentObservation(
                kind="error_occurred",
                message=f"Amazon login interaction failed: {exc}",
                data={"skill": self.name, "reason": "browser_interaction_failure"},
            )


class OpenOrdersPageSkill:
    name = "open_orders_page"
    description = "Open Amazon order history page."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        url = "https://www.amazon.com/gp/your-account/order-history"
        current = context.browser.current_url()
        if current and "amazon.com" not in current:
            return _missing_observation(
                "Amazon orders page not reachable after navigation",
                reason="orders_page_not_reachable",
                url=current,
            )
        try:
            context.browser.open_url(url)
            if "amazon.com" not in context.browser.current_url():
                return _missing_observation(
                    "Amazon orders page not reachable after navigation",
                    reason="orders_page_not_reachable",
                    url=url,
                )
            return AgentObservation(kind="page_loaded", message="Opened Amazon orders page", data={"url": url})
        except RuntimeError as exc:
            return AgentObservation(
                kind="error_occurred",
                message=f"Amazon orders page not reachable: {exc}",
                data={"url": url, "reason": "orders_page_not_reachable"},
            )


class GetLatestOrderSkill:
    name = "get_latest_order"
    description = "Locate latest Amazon order container."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        requested = arguments.get("selector")
        selector = _resolve_selector(context, "order_container", requested)
        try:
            context.browser.wait_for_selector(selector)
            return AgentObservation(
                kind="element_found",
                message="Latest order container located",
                data={"selector": selector},
            )
        except RuntimeError as exc:
            return _missing_observation(
                f"Latest order not found using selector '{selector}': {exc}",
                reason="latest_order_not_found",
                selector=selector,
            )


class ExtractOrderStatusSkill:
    name = "extract_order_status"
    description = "Extract delivery status text from latest Amazon order."

    def execute(self, arguments: dict[str, str], context: SkillContext) -> AgentObservation:
        requested = arguments.get("selector")
        selector = _resolve_selector(context, "order_status", requested)

        try:
            if not context.browser.selector_exists(selector):
                return _missing_observation(
                    "Order status selector not found on page",
                    reason="status_selector_not_found",
                    selector=selector,
                )

            text = context.browser.extract_text(selector)
            if not text.strip():
                return _missing_observation(
                    "Order status selector found but text was empty",
                    reason="status_text_empty",
                    selector=selector,
                )

            return AgentObservation(
                kind="text_extracted",
                message="Extracted latest order status",
                data={"selector": selector, "status": text},
            )
        except RuntimeError as exc:
            return _missing_observation(
                f"Order status extraction failed for selector '{selector}': {exc}",
                reason="extraction_failed",
                selector=selector,
            )
