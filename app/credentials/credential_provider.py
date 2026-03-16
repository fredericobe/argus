from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    @abstractmethod
    def get_secret(self, service: str, key: str) -> str | None:
        """Return secret value if available, otherwise None."""


class CompositeCredentialProvider(CredentialProvider):
    def __init__(self, providers: list[CredentialProvider]) -> None:
        self.providers = providers

    def get_secret(self, service: str, key: str) -> str | None:
        for provider in self.providers:
            value = provider.get_secret(service, key)
            if value:
                return value
        return None
