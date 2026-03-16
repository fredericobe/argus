from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArgusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: str = Field(alias="ARGUS_OPENAI_API_KEY")
    model_provider: str = Field(default="openai", alias="ARGUS_MODEL_PROVIDER")
    model_name: str = Field(default="gpt-4o-mini", alias="ARGUS_MODEL_NAME")
    model_temperature: float = Field(default=0.0, alias="ARGUS_MODEL_TEMPERATURE")
    model_max_tokens: int = Field(default=1200, alias="ARGUS_MODEL_MAX_TOKENS")

    headless: bool = Field(default=True, alias="ARGUS_HEADLESS")
    default_timeout_seconds: int = Field(default=20, alias="ARGUS_DEFAULT_TIMEOUT_SECONDS")
    navigation_timeout_seconds: int = Field(default=45, alias="ARGUS_NAVIGATION_TIMEOUT_SECONDS")
    session_state_path: Path = Field(default=Path(".argus/session_state.json"), alias="ARGUS_SESSION_STATE_PATH")
    screenshot_dir: Path = Field(default=Path("screenshots"), alias="ARGUS_SCREENSHOT_DIR")

    max_agent_steps: int = Field(default=12, alias="ARGUS_MAX_AGENT_STEPS")
    allowed_domains: list[str] = Field(
        default_factory=lambda: ["amazon.com", "www.amazon.com"],
        alias="ARGUS_ALLOWED_DOMAINS",
    )
    blocked_domains: list[str] = Field(default_factory=list, alias="ARGUS_BLOCKED_DOMAINS")
    log_level: str = Field(default="INFO", alias="ARGUS_LOG_LEVEL")

    @field_validator("allowed_domains", "blocked_domains", mode="before")
    @classmethod
    def _parse_csv_domains(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [v.strip().lower() for v in value if v and v.strip()]
        if isinstance(value, str):
            return [v.strip().lower() for v in value.split(",") if v.strip()]
        return []


@lru_cache(maxsize=1)
def get_settings() -> ArgusSettings:
    settings = ArgusSettings()
    settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
    settings.session_state_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
