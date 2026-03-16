from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import types
from typing import Any

from app.builder.code_provider import GeneratedCapabilityPackage

_ALLOWED_BUILTINS: dict[str, object] = {
    "len": len,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,
    "list": list,
    "set": set,
    "tuple": tuple,
    "enumerate": enumerate,
    "range": range,
    "abs": abs,
}


class GeneratedCapabilityExecutor:
    """Runs generated code under a narrow audited contract."""

    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        package: GeneratedCapabilityPackage,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        def _invoke() -> dict[str, Any]:
            globals_dict = {"__builtins__": _ALLOWED_BUILTINS}
            locals_dict: dict[str, Any] = {}
            exec(package.source_code, globals_dict, locals_dict)  # noqa: S102
            fn = locals_dict.get(package.entrypoint) or globals_dict.get(package.entrypoint)
            if not isinstance(fn, types.FunctionType):
                return {"success": False, "data": None, "evidence": [], "error": "Entrypoint not callable"}

            try:
                result = fn(arguments, context)
            except TypeError:
                result = fn(arguments)
            if not isinstance(result, dict):
                return {"success": False, "data": None, "evidence": [], "error": "Entrypoint must return dict"}
            success_flag = result.get("success")
            if success_flag is None:
                success_flag = result.get("status") == "ok"
            return {
                "success": bool(success_flag),
                "data": result.get("data"),
                "evidence": result.get("evidence", []),
                "error": result.get("error"),
            }

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_invoke)
            try:
                return future.result(timeout=self.timeout_seconds)
            except TimeoutError:
                return {"success": False, "data": None, "evidence": [], "error": "Execution timeout"}
            except Exception as exc:  # noqa: BLE001
                return {"success": False, "data": None, "evidence": [], "error": str(exc)}


class DomainBoundContext:
    """Context object exposed to generated code for domain-governed operations."""

    def __init__(self, allowed_domains: set[str], call_api: Callable[[str, dict[str, Any]], Any]) -> None:
        self.allowed_domains = allowed_domains
        self._call_api = call_api

    def api_call(self, domain: str, payload: dict[str, Any]) -> Any:
        normalized = domain.strip().lower()
        if normalized not in self.allowed_domains:
            raise RuntimeError(f"Undeclared domain access: {normalized}")
        return self._call_api(normalized, payload)
