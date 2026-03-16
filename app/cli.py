import typer

from app.capabilities.memory import CapabilityMemory
from app.capabilities.models import CapabilityType
from app.capabilities.registry import CapabilityRegistry
from app.config.settings import get_settings
from app.skills.registry import DEFAULT_SKILLS, stable_capabilities_from_skills
from app.tasks.amazon_order_status import AmazonOrderStatusTask, AmazonTaskRunOptions
from app.utils.logging import configure_logging

app = typer.Typer(help="Argus: AI-powered web operator agent")


def _bootstrap_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for capability in stable_capabilities_from_skills(DEFAULT_SKILLS):
        registry.register(capability)
    return registry


@app.command("show-config")
def show_config() -> None:
    """Show non-secret runtime configuration."""
    settings = get_settings()
    configure_logging(settings.log_level)

    safe_dump = settings.model_dump()
    safe_dump["openai_api_key"] = "***"
    typer.echo(safe_dump)


@app.command("list-skills")
def list_skills() -> None:
    """List built-in high-level skills available to the planner."""
    for skill in sorted(DEFAULT_SKILLS, key=lambda s: s.name):
        typer.echo(f"- {skill.name}: {skill.description}")


@app.command("list-capabilities")
def list_capabilities(kind: str = typer.Option("all", help="all|stable|learned|generated")) -> None:
    """List capabilities from the registry."""
    registry = _bootstrap_registry()
    mapping = {
        "stable": CapabilityType.STABLE,
        "learned": CapabilityType.LEARNED,
        "generated": CapabilityType.GENERATED_TEMPORARY,
    }
    capability_type = mapping.get(kind)
    capabilities = registry.list_capabilities(capability_type=capability_type) if capability_type else registry.list_capabilities()
    for cap in capabilities:
        typer.echo(f"- {cap.name} ({cap.capability_type.value}, {cap.status.value}, {cap.implementation_kind.value})")


@app.command("show-capability-memory")
def show_capability_memory() -> None:
    """Inspect stored capability usage memory."""
    settings = get_settings()
    memory = CapabilityMemory(settings.capability_storage_path)
    for record in memory.all_records():
        typer.echo(record.model_dump(mode="json"))


@app.command("run-amazon-task")
def run_amazon_task(
    request: str = typer.Argument(..., help="Natural language request to execute"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in headed mode"),
    max_steps: int | None = typer.Option(None, "--max-steps", min=1, help="Override max agent steps"),
) -> None:
    """Run Amazon order status workflow."""
    settings = get_settings()
    configure_logging(settings.log_level)

    task = AmazonOrderStatusTask(settings)
    result = task.run(
        user_request=request,
        options=AmazonTaskRunOptions(headed=headed, max_steps=max_steps),
    )
    typer.echo({"status_summary": result.status_summary, "steps_taken": result.steps_taken})
