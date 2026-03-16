from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.capabilities.models import RiskLevel


class CapabilitySpec(BaseModel):
    """Especificação declarativa usada para solicitar geração de nova capacidade."""
    name: str
    task: str
    description: str
    allowed_domains: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
