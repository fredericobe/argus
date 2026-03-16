from __future__ import annotations

from dataclasses import dataclass

from app.builder.sandbox import SandboxResult
from app.capabilities.models import Capability
from app.safety.safety_policy import SafetyPolicy, SafetyViolationError


@dataclass(slots=True)
class EvaluationResult:
    accepted: bool
    promotable: bool
    reason: str
    score: float
    evidence_quality: float


class CapabilityEvaluator:
    def __init__(self, safety_policy: SafetyPolicy, strict_mode: bool = True) -> None:
        self.safety_policy = safety_policy
        self.strict_mode = strict_mode

    def evaluate(self, capability: Capability, result: SandboxResult) -> EvaluationResult:
        if not result.passed:
            return EvaluationResult(False, False, result.reason or "sandbox failed", score=0.0, evidence_quality=0.0)

        evidence = result.output.get("evidence") if isinstance(result.output, dict) else None
        evidence_quality = float(len(evidence)) if isinstance(evidence, list) else 0.0
        if self.strict_mode and evidence_quality <= 0:
            return EvaluationResult(False, False, "missing evidence", score=0.0, evidence_quality=0.0)

        try:
            for domain in capability.allowed_domains:
                self.safety_policy.validate_skill("navigate_to_url", {"url": f"https://{domain}"})
        except SafetyViolationError as exc:
            return EvaluationResult(False, False, f"unsafe domain usage: {exc}", score=0.0, evidence_quality=evidence_quality)

        score = min(1.0, 0.6 + min(evidence_quality, 4.0) * 0.1)
        promotable = True
        return EvaluationResult(True, promotable, "evaluation accepted", score=score, evidence_quality=evidence_quality)
