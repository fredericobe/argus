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


class CapabilityEvaluator:
    def __init__(self, safety_policy: SafetyPolicy, strict_mode: bool = True) -> None:
        self.safety_policy = safety_policy
        self.strict_mode = strict_mode

    def evaluate(self, capability: Capability, result: SandboxResult) -> EvaluationResult:
        if not result.passed:
            return EvaluationResult(accepted=False, promotable=False, reason=result.reason or "sandbox failed")

        evidence = result.output.get("evidence") if isinstance(result.output, dict) else None
        if self.strict_mode and (not isinstance(evidence, list) or not evidence):
            return EvaluationResult(accepted=False, promotable=False, reason="missing evidence")

        try:
            for domain in capability.allowed_domains:
                self.safety_policy.validate_skill("navigate_to_url", {"url": f"https://{domain}"})
        except SafetyViolationError as exc:
            return EvaluationResult(accepted=False, promotable=False, reason=f"unsafe domain usage: {exc}")

        return EvaluationResult(accepted=True, promotable=True, reason="evaluation accepted")
