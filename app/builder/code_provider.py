from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.builder.spec import CapabilitySpec


@dataclass(slots=True)
class GeneratedCapabilityPackage:
    """Pacote de saída de geração com código, entrypoint e metadados."""
    source_code: str
    entrypoint: str
    manifest: dict[str, str]


class CodeGenerationProvider(Protocol):
    """Contrato para provedores de geração de código desacoplados do runtime."""
    def generate(self, spec: CapabilitySpec) -> GeneratedCapabilityPackage: ...


class StubCodeGenerationProvider:
    """Provider determinístico e seguro para desenvolvimento local e testes."""

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
