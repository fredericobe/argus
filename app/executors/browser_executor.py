from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext, Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from app.config.settings import ArgusSettings


class BrowserExecutor:
    """Low-level browser executor. No task-specific logic."""

    def __init__(self, settings: ArgusSettings) -> None:
        self.settings = settings
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def start(self) -> None:
        try:
            self._playwright = sync_playwright().start()
            browser = self._playwright.chromium.launch(headless=self.settings.headless)

            context_options: dict[str, object] = {"viewport": {"width": 1366, "height": 900}}
            if self.settings.session_state_path.exists():
                context_options["storage_state"] = str(self.settings.session_state_path)

            self._context = browser.new_context(**context_options)
            self._context.set_default_timeout(self.settings.default_timeout_seconds * 1000)
            self._page = self._context.new_page()
        except PlaywrightError as exc:
            raise RuntimeError(f"Failed to start browser executor: {exc}") from exc

    def close(self) -> None:
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser not started")
        return self._page

    def open_url(self, url: str) -> str:
        try:
            self.page.goto(url, timeout=self.settings.navigation_timeout_seconds * 1000)
            return url
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            raise RuntimeError(f"Navigation failed for {url}: {exc}") from exc

    def click(self, selector: str) -> None:
        try:
            self.page.click(selector)
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            raise RuntimeError(f"Click failed for selector '{selector}': {exc}") from exc

    def type_text(self, selector: str, text: str) -> None:
        try:
            self.page.fill(selector, text)
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            raise RuntimeError(f"Typing failed for selector '{selector}': {exc}") from exc

    def extract_text(self, selector: str) -> str:
        try:
            return self.page.locator(selector).first.inner_text().strip()
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            raise RuntimeError(f"Text extraction failed for selector '{selector}': {exc}") from exc

    def wait_for_selector(self, selector: str, timeout_ms: int | None = None) -> None:
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms)
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            raise RuntimeError(f"Selector wait failed for '{selector}': {exc}") from exc

    def selector_exists(self, selector: str) -> bool:
        try:
            return self.page.locator(selector).first.count() > 0
        except PlaywrightError:
            return False

    def take_screenshot(self, filename: str = "argus-debug.png") -> str:
        path = Path(self.settings.screenshot_dir) / filename
        self.page.screenshot(path=path.as_posix(), full_page=True)
        return path.as_posix()

    def current_url(self) -> str:
        return self.page.url

    def save_session_state(self) -> None:
        if not self._context:
            raise RuntimeError("Browser not started")
        self.settings.session_state_path.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=self.settings.session_state_path.as_posix())
