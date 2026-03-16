from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.builder.spec import CapabilitySpec


@dataclass(slots=True)
class GeneratedCapabilityPackage:
    capability_id: str = ""
    version: str = "1.0.0"
    declared_domains: list[str] = field(default_factory=list)
    entrypoint: str = "run"
    metadata: dict[str, str] = field(default_factory=dict)
    source_code: str = ""
    manifest: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.manifest and not self.metadata:
            self.metadata = dict(self.manifest)
        if self.metadata and not self.manifest:
            self.manifest = dict(self.metadata)


class CodeGenerationProvider(Protocol):
    def generate(self, spec: CapabilitySpec) -> GeneratedCapabilityPackage: ...


class StubCodeGenerationProvider:
    def generate(self, spec: CapabilitySpec) -> GeneratedCapabilityPackage:
        source = (
            "def run(arguments, context):\n"
            "    task = arguments.get('task', '')\n"
            "    return {\n"
            "        'success': True,\n"
            "        'data': {'summary': f'Generated capability handled: {task}'},\n"
            "        'evidence': [f'spec:{spec_name}'],\n"
            "        'error': None,\n"
            "    }\n"
        ).replace("{spec_name}", spec.name)
        return GeneratedCapabilityPackage(
            capability_id=f"generated::{spec.name}",
            version="1.0.0",
            declared_domains=spec.allowed_domains,
            entrypoint="run",
            metadata={"name": spec.name, "mode": "stub_generated"},
            source_code=source,
        )
