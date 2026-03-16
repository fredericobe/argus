from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityType(str, Enum):
    STABLE = "stable"
    LEARNED = "learned"
    GENERATED_TEMPORARY = "generated_temporary"
    GENERATED_CANDIDATE = "generated_candidate"


class CapabilityStatus(str, Enum):
    STABLE = "stable"
    GENERATED_TEMPORARY = "generated_temporary"
    GENERATED_CANDIDATE = "generated_candidate"
    APPROVED_STABLE = "approved_stable"
    REJECTED = "rejected"


class ImplementationKind(str, Enum):
    SKILL = "skill"
    BROWSER_WORKFLOW = "browser_workflow"
    API_ADAPTER = "api_adapter"
    GENERATED_CODE = "generated_code"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Capability(BaseModel):
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    status: CapabilityStatus
    risk_level: RiskLevel = RiskLevel.LOW
    capability_type: CapabilityType
    allowed_domains: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    implementation_kind: ImplementationKind
    tags: list[str] = Field(default_factory=list)
    author: str = "argus"
    source: str = "internal"
    implementation_ref: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityUsageRecord(BaseModel):
    capability_id: str
    task: str
    task_signature: str = ""
    success: bool
    evaluator_score: float = 0.0
    evidence_quality: float = 0.0
    execution_count: int = 1
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
