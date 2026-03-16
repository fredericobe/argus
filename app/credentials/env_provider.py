import os

from app.credentials.credential_provider import CredentialProvider


class EnvCredentialProvider(CredentialProvider):
    def get_secret(self, service: str, key: str) -> str | None:
        env_key = f"ARGUS_{service}_{key}".upper().replace(".", "_")
        return os.getenv(env_key)
