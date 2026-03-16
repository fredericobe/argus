from app.builder.code_provider import GeneratedCapabilityPackage
from app.builder.sandbox import SandboxRunner


def test_sandbox_accepts_safe_package() -> None:
    sandbox = SandboxRunner(enabled=True, timeout_seconds=1)
    package = GeneratedCapabilityPackage(
        source_code="def run(arguments):\n    return {'status':'ok'}\n",
        entrypoint="run",
        manifest={"name": "ok"},
    )
    assert sandbox.validate_package(package).passed is True
    assert sandbox.execute(package, {"task": "x"}).passed is True


def test_sandbox_rejects_invalid_package_and_failure_recorded() -> None:
    sandbox = SandboxRunner(enabled=True, timeout_seconds=1)
    invalid = GeneratedCapabilityPackage(source_code="def nope():\n    pass\n", entrypoint="nope", manifest={})
    assert sandbox.validate_package(invalid).passed is False

    failing = GeneratedCapabilityPackage(
        source_code="def run(arguments):\n    raise RuntimeError('boom')\n",
        entrypoint="run",
        manifest={},
    )
    result = sandbox.execute(failing, {"task": "x"})
    assert result.passed is False
