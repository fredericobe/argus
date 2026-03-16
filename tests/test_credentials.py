from app.credentials.credential_provider import CompositeCredentialProvider, CredentialProvider


class DummyProvider(CredentialProvider):
    def __init__(self, value: str | None) -> None:
        self.value = value

    def get_secret(self, service: str, key: str) -> str | None:
        return self.value


def test_composite_returns_first_hit() -> None:
    provider = CompositeCredentialProvider([DummyProvider(None), DummyProvider("secret")])
    assert provider.get_secret("amazon", "username") == "secret"
