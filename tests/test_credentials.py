from app.credentials.credential_provider import CompositeCredentialProvider, CredentialProvider
from app.credentials.env_provider import EnvCredentialProvider


class DummyProvider(CredentialProvider):
    def __init__(self, value: str | None) -> None:
        self.value = value

    def get_secret(self, service: str, key: str) -> str | None:
        return self.value


def test_composite_returns_first_hit() -> None:
    provider = CompositeCredentialProvider([DummyProvider(None), DummyProvider("secret")])
    assert provider.get_secret("amazon", "username") == "secret"


def test_composite_returns_none_when_missing() -> None:
    provider = CompositeCredentialProvider([DummyProvider(None), DummyProvider(None)])
    assert provider.get_secret("amazon", "username") is None


def test_env_provider_formats_key(monkeypatch) -> None:
    monkeypatch.setenv("ARGUS_AMAZON_USERNAME", "alice")
    provider = EnvCredentialProvider()
    assert provider.get_secret("amazon", "username") == "alice"
