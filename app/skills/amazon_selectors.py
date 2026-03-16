from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SelectorSet:
    primary: str
    fallbacks: tuple[str, ...] = ()

    def all(self) -> list[str]:
        return [self.primary, *self.fallbacks]


AMAZON_SELECTORS = {
    "login_email": SelectorSet("input[name='email']", ("#ap_email",)),
    "login_continue": SelectorSet("input#continue", ("#continue",)),
    "login_password": SelectorSet("input[name='password']", ("#ap_password",)),
    "login_submit": SelectorSet("input#signInSubmit", ("#signInSubmit",)),
    "order_container": SelectorSet(
        "div.order",
        ("div.your-orders-content-container div.order-card", "div.order-card"),
    ),
    "order_status": SelectorSet(
        "div.order span.a-color-success",
        (
            "div.order span[data-test-id='order-status']",
            "div.order-card span.a-color-success",
        ),
    ),
}
