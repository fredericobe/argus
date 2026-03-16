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
        host = self._extract_normalized_hostname(url)
        if not host:
            raise SafetyViolationError("URL must contain a valid domain")

        if self._matches_any_domain(host, self.blocked_domains):
            raise SafetyViolationError(f"Blocked domain access denied: {host}")

        if self.allowed_domains and not self._matches_any_domain(host, self.allowed_domains):
            raise SafetyViolationError(f"Domain not in allowlist: {host}")

    @classmethod
    def _matches_any_domain(cls, host: str, domains: list[str]) -> bool:
        return any(
            cls._is_exact_or_subdomain(host, cls._normalize_domain_rule(domain))
            for domain in domains
            if domain
        )

    @staticmethod
    def _extract_normalized_hostname(url: str) -> str:
        # urlparse only extracts hostname reliably when a netloc exists.
        # Support values that may omit the scheme, e.g. "amazon.com:443/path".
        parsed = urlparse(url if "://" in url else f"//{url}", scheme="https")
        host = parsed.hostname
        if not host:
            return ""

        return SafetyPolicy._normalize_domain_rule(host)

    @staticmethod
    def _normalize_domain_rule(domain: str) -> str:
        normalized = domain.strip().lower().strip(".")
        if not normalized:
            return ""

        # Normalize IDN domains deterministically.
        try:
            return normalized.encode("idna").decode("ascii")
        except UnicodeError:
            return normalized

    @staticmethod
    def _is_exact_or_subdomain(host: str, domain: str) -> bool:
        return host == domain or host.endswith(f".{domain}")

    @staticmethod
    def _is_destructive(skill_name: str, arguments: dict[str, str]) -> bool:
        risky_skills = {"place_order", "submit_payment", "delete_account_data", "change_account_settings"}
        if skill_name in risky_skills:
            return True

        haystack = " ".join([skill_name, *arguments.values()]).lower()
        risky_keywords = ["buy", "purchase", "payment", "delete", "remove", "account change"]
        return any(k in haystack for k in risky_keywords)
