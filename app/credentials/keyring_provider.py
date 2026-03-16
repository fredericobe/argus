import keyring

from app.credentials.credential_provider import CredentialProvider


class KeyringCredentialProvider(CredentialProvider):
    def __init__(self, namespace: str = "argus") -> None:
        self.namespace = namespace

    def get_secret(self, service: str, key: str) -> str | None:
        return keyring.get_password(self.namespace, f"{service}.{key}")
