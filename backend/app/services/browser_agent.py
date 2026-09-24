import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Browser, Page, ConsoleMessage, Request, Response

from app.core.config import settings
from app.core.execution.runtime_context import RuntimeContext

logger = logging.getLogger(__name__)

class BrowserAgent:
    """
    Playwright Browser Automation Agent for LISA.
    Executes browser actions, captures DOM info, console logs, network requests, and screenshots as evidence.
    """

    def __init__(self, run_id: str, evidence_dir: Path, step_timeout: int = 10000):
        self.run_id = run_id
        self.evidence_dir = evidence_dir
        self.step_timeout = step_timeout
        self.screenshots_dir = evidence_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        self.console_logs: List[Dict[str, Any]] = []
        self.network_requests: List[Dict[str, Any]] = []
        self.action_logs: List[str] = []

    def _log_action(self, action: str, details: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {action} {details}".strip()
        self.action_logs.append(log_entry)
        logger.info(f"BrowserAgent ({self.run_id}): {log_entry}")

    async def start_browser(self, headless: bool = True):
        """Initializes Playwright Chromium instance."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
        self.page = await context.new_page()

        # Wire console & network monitoring
        self.page.on("console", self._handle_console)
        self.page.on("request", self._handle_request)
        self.page.on("response", self._handle_response)

        self._log_action("INITIALIZE", "Playwright Chromium Headless Browser")

    def _handle_console(self, msg: ConsoleMessage):
        self.console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    def _handle_request(self, req: Request):
        self.network_requests.append({
            "url": req.url,
            "method": req.method,
            "resource_type": req.resource_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    def _handle_response(self, res: Response):
        for req in self.network_requests:
            if req.get("url") == res.url and "status" not in req:
                req["status"] = res.status
                req["ok"] = res.ok
                break

    async def open_url(self, url: str) -> Tuple[bool, str]:
        """Navigates browser to target URL."""
        if not self.page:
            return False, "Browser page not initialized."
        try:
            self._log_action("OPEN", url)
            res = await self.page.goto(url, wait_until="networkidle", timeout=15000)
            status = res.status if res else 200
            return status < 400, f"Navigated to {url} (HTTP {status})"
        except Exception as e:
            self._log_action("OPEN_ERROR", f"{url} - {str(e)}")
            return False, str(e)

    async def click(self, selector: str) -> Tuple[bool, str]:
        """Clicks an element by selector or text content."""
        if not self.page:
            return False, "Browser page not initialized."
        try:
            self._log_action("FIND", f"Element matching '{selector}'")
            # Try text selector if simple string
            loc = self.page.locator(selector).first
            if not await loc.count():
                loc = self.page.get_by_text(selector).first

            self._log_action("CLICK", selector)
            await loc.click(timeout=self.step_timeout)
            return True, f"Clicked element '{selector}'"
        except Exception as e:
            self._log_action("CLICK_ERROR", f"{selector} - {str(e)}")
            return False, str(e)

    async def type_text(self, selector: str, text: str) -> Tuple[bool, str]:
        """Fills input text field."""
        if not self.page:
            return False, "Browser page not initialized."
        try:
            self._log_action("FIND", f"Input field '{selector}'")
            loc = self.page.locator(selector).first
            if not await loc.count():
                loc = self.page.get_by_placeholder(selector).first

            self._log_action("TYPE", f"'{text}' into '{selector}'")
            await loc.fill(text, timeout=self.step_timeout)
            return True, f"Typed text into '{selector}'"
        except Exception as e:
            self._log_action("TYPE_ERROR", f"{selector} - {str(e)}")
            return False, str(e)

    async def select_option(self, selector: str, value: str) -> Tuple[bool, str]:
        """Selects dropdown option."""
        if not self.page:
            return False, "Browser page not initialized."
        try:
            self._log_action("SELECT", f"Option '{value}' in '{selector}'")
            await self.page.select_option(selector, value, timeout=5000)
            return True, f"Selected option '{value}'"
        except Exception as e:
            return False, str(e)

    async def press_key(self, key: str) -> Tuple[bool, str]:
        """Presses a keyboard key."""
        if not self.page:
            return False, "Browser page not initialized."
        try:
            self._log_action("PRESS_KEY", key)
            await self.page.keyboard.press(key)
            return True, f"Pressed key '{key}'"
        except Exception as e:
            return False, str(e)

    async def get_page_title(self) -> str:
        """Returns current page title."""
        if not self.page:
            return ""
        title = await self.page.title()
        self._log_action("PAGE_TITLE", f"'{title}'")
        return title

    async def get_page_text(self) -> str:
        """Returns visible body text snippet."""
        if not self.page:
            return ""
        text = await self.page.inner_text("body")
        return text[:2000]

    async def take_screenshot(self, name: str) -> Optional[str]:
        """Captures screenshot and returns relative path."""
        if not self.page:
            return None
        file_name = f"{name}_{datetime.datetime.now().strftime('%Y%m%m_%H%M%S')}.png"
        full_path = self.screenshots_dir / file_name
        try:
            await self.page.screenshot(path=str(full_path), full_page=True)
            self._log_action("SCREENSHOT", f"Saved to {file_name}")
            return f"screenshots/{file_name}"
        except Exception as e:
            self._log_action("SCREENSHOT_ERROR", str(e))
            return None

    async def execute_step(self, step: Dict[str, Any], base_url: str | RuntimeContext) -> Tuple[bool, str, Optional[str]]:
        """Executes a single test step object and captures screenshot."""
        runtime_context = base_url if isinstance(base_url, RuntimeContext) else None
        base_url = runtime_context.frontend_base_url if runtime_context else base_url
        action = step.get("action", "").lower()
        target = step.get("target", "")
        value = step.get("value", "")

        screenshot_path = None
        success = False
        message = ""

        if action == "open_url":
            full_url = target if target.startswith("http") else f"{base_url.rstrip('/')}/{target.lstrip('/')}"
            if (runtime_context and not runtime_context.validate_target_url(full_url)) or urlparse(full_url).netloc != urlparse(base_url).netloc:
                return False, f"Invalid test target: {full_url} is outside the current runtime {base_url}", None
            success, message = await self.open_url(full_url)
        elif action == "click":
            success, message = await self.click(target)
        elif action in ["type_text", "type", "fill"]:
            val = value or step.get("expected", "test@example.com")
            success, message = await self.type_text(target, val)
        elif action == "select_option":
            success, message = await self.select_option(target, value)
        elif action == "press_key":
            success, message = await self.press_key(target or "Enter")
        elif action in ["get_page_title", "title"]:
            title = await self.get_page_title()
            success = bool(title)
            message = f"Page title: '{title}'"
        elif action in ["get_page_text", "text"]:
            text = await self.get_page_text()
            success = bool(text.strip())
            message = f"Page text captured ({len(text)} characters)"
        else:
            success, message = False, f"Unsupported or unverifiable browser action '{action}'"

        # Capture step screenshot
        step_num = step.get("step_number", 1)
        screenshot_path = await self.take_screenshot(f"step_{step_num}_{action}")

        return success, message, screenshot_path

    async def close(self):
        """Closes browser session."""
        if self.browser:
            self._log_action("CLOSE", "Playwright Browser session closed")
            try:
                await asyncio.wait_for(asyncio.shield(self.browser.close()), timeout=5)
            except asyncio.TimeoutError:
                logger.warning("Playwright browser close timed out for run %s", self.run_id)
        if self.playwright:
            try:
                await asyncio.wait_for(asyncio.shield(self.playwright.stop()), timeout=5)
            except asyncio.TimeoutError:
                logger.warning("Playwright shutdown timed out for run %s", self.run_id)
