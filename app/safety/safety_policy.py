from dataclasses import dataclass
from urllib.parse import urlparse


class SafetyViolationError(RuntimeError):
    """Raised when an operation violates safety policy."""


@dataclass(slots=True)
class SafetyPolicy:
    allowed_domains: list[str]
    blocked_domains: list[str]
    max_steps: int

    def check_step_limit(self, step: int) -> None:
        if step > self.max_steps:
            raise SafetyViolationError(f"Step limit exceeded: {step} > {self.max_steps}")

    def validate_skill(self, skill_name: str, arguments: dict[str, str]) -> None:
        url = arguments.get("url")
        if url:
            self._check_domain(url)

        if skill_name == "navigate_to_url" and not url:
            raise SafetyViolationError("navigate_to_url requires 'url' argument")

    def requires_confirmation_for_skill(self, skill_name: str, arguments: dict[str, str]) -> bool:
        return self._is_destructive(skill_name, arguments)

    def _check_domain(self, url: str) -> None:
        netloc = urlparse(url).netloc.lower()
        if not netloc:
            raise SafetyViolationError("URL must contain a valid domain")

        if any(blocked in netloc for blocked in self.blocked_domains):
            raise SafetyViolationError(f"Blocked domain access denied: {netloc}")

        if self.allowed_domains and not any(allowed in netloc for allowed in self.allowed_domains):
            raise SafetyViolationError(f"Domain not in allowlist: {netloc}")

    @staticmethod
    def _is_destructive(skill_name: str, arguments: dict[str, str]) -> bool:
        risky_skills = {"place_order", "submit_payment", "delete_account_data", "change_account_settings"}
        if skill_name in risky_skills:
            return True

        haystack = " ".join([skill_name, *arguments.values()]).lower()
        risky_keywords = ["buy", "purchase", "payment", "delete", "remove", "account change"]
        return any(k in haystack for k in risky_keywords)
