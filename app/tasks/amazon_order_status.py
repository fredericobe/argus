from dataclasses import dataclass
import logging

from app.config.settings import ArgusSettings
from app.credentials.credential_provider import CompositeCredentialProvider
from app.credentials.env_provider import EnvCredentialProvider
from app.credentials.keyring_provider import KeyringCredentialProvider
from app.executors.browser_executor import BrowserExecutor
from app.planner.agent_runtime import AgentRuntime
from app.planner.planner import LLMPlanner
from app.safety.safety_policy import SafetyPolicy
from app.skills.base import SkillContext
from app.skills.registry import DEFAULT_SKILLS, SkillRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class AmazonTaskRunOptions:
    headed: bool = False
    max_steps: int | None = None


@dataclass(slots=True)
class AmazonOrderStatusResult:
    status_summary: str
    steps_taken: int


class AmazonOrderStatusTask:
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
        skill_context = SkillContext(browser=browser, credentials=self.credentials)
        runtime = AgentRuntime(
            planner=planner,
            skill_registry=skill_registry,
            skill_context=skill_context,
            safety_policy=policy,
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
