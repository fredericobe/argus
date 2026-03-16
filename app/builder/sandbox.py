from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from app.builder.code_provider import GeneratedCapabilityPackage
from app.capabilities.generated_executor import DomainBoundContext, GeneratedCapabilityExecutor

_ALLOWED_IMPORTS = {"json", "math", "re", "datetime"}
_BLOCKED_CALLS = {"open", "exec", "eval", "compile", "__import__"}


@dataclass(slots=True)
class SandboxResult:
    passed: bool
    output: dict[str, object]
    reason: str = ""


class SandboxRunner:
    """In-process sandbox with validation architecture ready for containerized isolation."""

    def __init__(self, enabled: bool, timeout_seconds: int, temp_root: Path | None = None) -> None:
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.temp_root = temp_root
        self.executor = GeneratedCapabilityExecutor(timeout_seconds=timeout_seconds)

    def validate_package(self, package: GeneratedCapabilityPackage) -> SandboxResult:
        if not self.enabled:
            return SandboxResult(False, {}, "Sandbox is disabled")
        if not package.entrypoint:
            return SandboxResult(False, {}, "Invalid package metadata")
        if not package.source_code or len(package.source_code) > 50_000:
            return SandboxResult(False, {}, "Invalid source size")

        try:
            tree = ast.parse(package.source_code)
        except SyntaxError as exc:
            return SandboxResult(False, {}, f"Syntax error: {exc}")

        entrypoint_found = False
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == package.entrypoint:
                entrypoint_found = True
                if len(node.args.args) < 1:
                    return SandboxResult(False, {}, "Entrypoint must accept run(arguments[, context])")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_CALLS:
                return SandboxResult(False, {}, f"Blocked call detected: {node.func.id}")

        if not entrypoint_found:
            return SandboxResult(False, {}, "Entrypoint not found")

        disallowed = sorted(name for name in imports if name not in _ALLOWED_IMPORTS)
        if disallowed:
            return SandboxResult(False, {"disallowed_imports": disallowed}, "Disallowed imports detected")

        return SandboxResult(True, {"validated": True, "imports": sorted(imports)})

    def execute(self, package: GeneratedCapabilityPackage, arguments: dict[str, Any]) -> SandboxResult:
        validation = self.validate_package(package)
        if not validation.passed:
            return validation

        with TemporaryDirectory(dir=self.temp_root) as tmp_dir:
            allowed_tmp = Path(tmp_dir)

            def _api_call(_domain: str, _payload: dict[str, Any]) -> Any:
                return {"ok": True, "echo": _payload}

            ctx = {
                "api": DomainBoundContext(set(package.declared_domains), _api_call),
                "sandbox": {
                    "temp_dir": str(allowed_tmp),
                    "filesystem_writes_restricted": True,
                    "network_restricted_to_declared_domains": True,
                },
            }
            result = self.executor.run(package=package, arguments=arguments, context=ctx)
            if result.get("success"):
                return SandboxResult(True, result)
            return SandboxResult(False, result, str(result.get("error") or "sandbox execution failed"))
