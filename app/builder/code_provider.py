from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.builder.spec import CapabilitySpec


@dataclass(slots=True)
class GeneratedCapabilityPackage:
    source_code: str
    entrypoint: str
    manifest: dict[str, str]


class CodeGenerationProvider(Protocol):
    def generate(self, spec: CapabilitySpec) -> GeneratedCapabilityPackage: ...


class StubCodeGenerationProvider:
    """Safe deterministic provider used for local development and tests."""

    def generate(self, spec: CapabilitySpec) -> GeneratedCapabilityPackage:
        source = (
            "def run(arguments):\n"
            "    task = arguments.get('task', '')\n"
            "    return {\n"
            "        'status': 'ok',\n"
            "        'summary': f'Generated capability handled: {task}',\n"
            "        'evidence': [f'spec:{spec_name}'],\n"
            "    }\n"
        ).replace("{spec_name}", spec.name)
        return GeneratedCapabilityPackage(
            source_code=source,
            entrypoint="run",
            manifest={"name": spec.name, "mode": "stub_generated"},
        )
