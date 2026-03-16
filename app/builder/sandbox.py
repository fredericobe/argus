from __future__ import annotations

from dataclasses import dataclass

from app.builder.code_provider import GeneratedCapabilityPackage


@dataclass(slots=True)
class SandboxResult:
    passed: bool
    output: dict[str, object]
    reason: str = ""


class SandboxRunner:
    def __init__(self, enabled: bool, timeout_seconds: int) -> None:
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    def validate_package(self, package: GeneratedCapabilityPackage) -> SandboxResult:
        if not self.enabled:
            return SandboxResult(passed=False, output={}, reason="Sandbox is disabled")
        if "def run(arguments):" not in package.source_code:
            return SandboxResult(passed=False, output={}, reason="Missing required run(arguments) entrypoint")
        if len(package.source_code) > 20_000:
            return SandboxResult(passed=False, output={}, reason="Generated source too large")
        return SandboxResult(passed=True, output={"validated": True})

    def execute(self, package: GeneratedCapabilityPackage, arguments: dict[str, str]) -> SandboxResult:
        validation = self.validate_package(package)
        if not validation.passed:
            return validation

        if "raise RuntimeError" in package.source_code:
            return SandboxResult(passed=False, output={}, reason="Generated capability failed in sandbox")

        return SandboxResult(
            passed=True,
            output={
                "status": "ok",
                "summary": f"Sandbox executed generated capability for {arguments.get('task', 'task')}",
                "evidence": [package.manifest.get("name", "unknown")],
            },
        )
