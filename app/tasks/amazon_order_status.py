from dataclasses import dataclass
import logging

from app.builder.builder import CapabilityBuilder
from app.builder.code_provider import StubCodeGenerationProvider
from app.builder.evaluator import CapabilityEvaluator
from app.builder.sandbox import SandboxRunner
from app.capabilities.lifecycle import CapabilityLifecycle
from app.capabilities.memory import CapabilityMemory
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.resolver import CapabilityResolver
from app.config.settings import ArgusSettings
from app.credentials.credential_provider import CompositeCredentialProvider
from app.credentials.env_provider import EnvCredentialProvider
from app.credentials.keyring_provider import KeyringCredentialProvider
from app.executors.browser_executor import BrowserExecutor
from app.planner.agent_runtime import AgentRuntime
from app.planner.planner import LLMPlanner
from app.safety.safety_policy import SafetyPolicy
from app.skills.base import SkillContext
from app.skills.registry import DEFAULT_SKILLS, SkillRegistry, stable_capabilities_from_skills

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class AmazonTaskRunOptions:
    """Opções de execução para o fluxo Amazon orientado a status de pedido."""
    headed: bool = False
    max_steps: int | None = None


@dataclass(slots=True)
class AmazonOrderStatusResult:
    """Resumo final da execução da tarefa Amazon para consumo de CLI/API."""
    status_summary: str
    steps_taken: int


class AmazonOrderStatusTask:
    """Caso de uso que monta dependências e executa runtime para pedidos Amazon."""
    def __init__(self, settings: ArgusSettings) -> None:
        self.settings = settings
        self.credentials = CompositeCredentialProvider(
            providers=[
                KeyringCredentialProvider(),
                EnvCredentialProvider(),
            ]
        )

    def run(self, user_request: str, options: AmazonTaskRunOptions | None = None) -> AmazonOrderStatusResult:
        options = options or AmazonTaskRunOptions()
        max_steps = options.max_steps or self.settings.max_agent_steps

        runtime_settings = self.settings.model_copy(
            update={
                "headless": not options.headed,
                "max_agent_steps": max_steps,
            }
        )

        planner = LLMPlanner(runtime_settings)
        browser = BrowserExecutor(runtime_settings)
        policy = SafetyPolicy(
            allowed_domains=runtime_settings.allowed_domains,
            blocked_domains=runtime_settings.blocked_domains,
            max_steps=runtime_settings.max_agent_steps,
        )

        skill_registry = SkillRegistry(DEFAULT_SKILLS)
        capability_registry = CapabilityRegistry()
        for capability in stable_capabilities_from_skills(DEFAULT_SKILLS):
            capability_registry.register(capability)

        memory = CapabilityMemory(runtime_settings.capability_storage_path)
        resolver = CapabilityResolver(capability_registry, policy)
        builder = CapabilityBuilder(
            code_provider=StubCodeGenerationProvider(),
            sandbox=SandboxRunner(
                enabled=runtime_settings.sandbox_enabled,
                timeout_seconds=runtime_settings.generated_capability_timeout_seconds,
            ),
            evaluator=CapabilityEvaluator(policy, strict_mode=runtime_settings.evaluator_strict_mode),
            lifecycle=CapabilityLifecycle(),
        )

        skill_context = SkillContext(browser=browser, credentials=self.credentials)
        runtime = AgentRuntime(
            planner=planner,
            skill_registry=skill_registry,
            skill_context=skill_context,
            safety_policy=policy,
            capability_registry=capability_registry,
            capability_resolver=resolver,
            capability_builder=builder,
            capability_memory=memory,
            enable_generated_capabilities=runtime_settings.enable_generated_capabilities,
        )

        initial_observation = (
            "For Amazon order status tasks, prefer skills in this order: "
            "open_orders_page -> login_amazon (if needed) -> get_latest_order -> extract_order_status -> finish."
        )

        browser.start()
        try:
            final_observation, audit = runtime.run(
                user_request=user_request,
                initial_observation=initial_observation,
            )
            logger.info("audit_steps=%s", len(audit))
            return AmazonOrderStatusResult(
                status_summary=final_observation.message,
                steps_taken=len(audit),
            )
        finally:
            try:
                browser.save_session_state()
            finally:
                browser.close()
