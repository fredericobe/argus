import typer

from app.config.settings import get_settings
from app.skills.registry import DEFAULT_SKILLS
from app.tasks.amazon_order_status import AmazonOrderStatusTask, AmazonTaskRunOptions
from app.utils.logging import configure_logging

app = typer.Typer(help="Argus: AI-powered web operator agent")


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
