"""Optional rendered browser execution with per-session isolation and bounded actions."""

from __future__ import annotations

import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse

from .errors import BrowserActionError, BrowserTimeoutError, BrowserUnavailableError, InvalidRequestError
from .fetch import validate_url
from .models import _omit_none
from .redaction import redact_text, redact_url
from .trust_engine import TrustEngine


@dataclass
class BrowserSession:
    session_id: str
    url: str
    status: str
    actions: list[dict] = field(default_factory=list)
    extracted: list[dict] = field(default_factory=list)
    title: str = ""
    text: str = ""
    html: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return _omit_none(asdict(self))


class BrowserEngine:
    """Run a fresh, isolated browser context for each request."""

    def __init__(
        self,
        trust_engine: TrustEngine | None = None,
        *,
        executable_path: str | None = None,
        action_timeout: float = 30.0,
        session_timeout: float = 90.0,
        allow_cross_origin: bool = False,
    ) -> None:
        self.trust_engine = trust_engine or TrustEngine()
        self.executable_path = executable_path or os.getenv("AGENTWEB_CHROMIUM_PATH")
        self.action_timeout = action_timeout
        self.session_timeout = session_timeout
        self.allow_cross_origin = allow_cross_origin

    def _browser_path(self) -> str | None:
        if self.executable_path:
            return self.executable_path if os.path.exists(self.executable_path) else None
        for candidate in ("chromium", "google-chrome", "chromium-browser"):
            path = shutil.which(candidate)
            if path:
                return path
        return None

    def open(self, url: str, actions: list[dict] | None = None) -> BrowserSession:
        """Render a URL and run documented actions, returning partial results on action failure."""
        validate_url(url)
        requested_url = url
        safe_url = redact_url(url)
        decision = self.trust_engine.should_fetch(requested_url)
        if not decision.allowed:
            raise BrowserActionError(decision.reason or "URL rejected by trust engine")
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise BrowserUnavailableError("browser extra is not installed; install agentweb[browser]") from error
        browser_path = self._browser_path()
        if not browser_path:
            raise BrowserUnavailableError("no Chromium-compatible browser executable is available")

        if actions is not None and not isinstance(actions, list):
            raise InvalidRequestError("actions must be a JSON array")
        requested_actions = actions or []
        if len(requested_actions) > 20:
            raise InvalidRequestError("browser action count cannot exceed 20")
        if any(isinstance(action, dict) and "credentials" in action for action in requested_actions):
            raise InvalidRequestError("credentials are not accepted in browser actions")
        started = time.monotonic()
        session = BrowserSession(session_id="sess_" + uuid.uuid4().hex[:16], url=safe_url, status="complete")
        origin = f"{urlparse(requested_url).scheme}://{urlparse(requested_url).netloc}"

        def allow_request(request) -> bool:
            if self.allow_cross_origin:
                return True
            parsed = urlparse(request.url)
            if parsed.scheme not in {"http", "https"}:
                return True
            return f"{parsed.scheme}://{parsed.netloc}" == origin

        with sync_playwright() as playwright:
            browser = None
            context = None
            try:
                browser = playwright.chromium.launch(
                    headless=True,
                    executable_path=browser_path,
                    timeout=int(self.session_timeout * 1000),
                    args=[
                        "--disable-dev-shm-usage",
                        "--disable-extensions",
                        "--disable-sync",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
                context = browser.new_context(
                    service_workers="block",
                    java_script_enabled=True,
                    ignore_https_errors=False,
                    viewport={"width": 1280, "height": 900},
                )
                context.route("**/*", lambda route: route.continue_() if allow_request(route.request) else route.abort())
                page = context.new_page()
                page.set_default_timeout(int(self.action_timeout * 1000))
                page.goto(requested_url, wait_until="domcontentloaded", timeout=int(self.action_timeout * 1000))
                session.url = redact_url(page.url)
                for index, action in enumerate(requested_actions):
                    if time.monotonic() - started > self.session_timeout:
                        raise BrowserTimeoutError("browser session exceeded the 90-second timeout")
                    if not isinstance(action, dict) or not action.get("type"):
                        session.warnings.append(f"action {index} ignored: action type is required")
                        continue
                    action_type = str(action["type"])
                    last_error: Exception | None = None
                    for attempt in range(2):
                        try:
                            self._run_action(page, action)
                            session.actions.append({"index": index, "type": action_type, "status": "complete"})
                            last_error = None
                            break
                        except PlaywrightTimeoutError as error:
                            last_error = error
                        except Exception as error:  # selectors and browser errors are partial failures
                            last_error = error
                    if last_error is not None:
                        session.status = "partial"
                        session.error = redact_text(f"action {index} ({action_type}) failed after retry: {last_error}")
                        session.warnings.append(session.error)
                        break
                session.title = page.title()
                full_text = page.locator("body").inner_text(timeout=int(self.action_timeout * 1000))
                full_html = page.content()
                session.text = full_text[:500_000]
                session.html = full_html[:2_000_000]
                if len(full_text) > len(session.text) or len(full_html) > len(session.html):
                    session.warnings.append("browser output was truncated at the configured size limit")
                session.extracted = list(self._extracted_for_page(page))
            except PlaywrightTimeoutError as error:
                session.status = "partial"
                session.error = redact_text(f"browser timeout: {error}")
                session.warnings.append(session.error)
            except BrowserTimeoutError:
                raise
            except Exception as error:
                raise BrowserActionError(redact_text(str(error))) from error
            finally:
                if context is not None:
                    context.close()
                if browser is not None:
                    browser.close()
        return session

    def _run_action(self, page, action: dict) -> None:
        action_type = str(action["type"])
        selector = action.get("selector")
        if action_type == "click":
            if not selector:
                raise BrowserActionError("click requires selector")
            page.locator(selector).click(timeout=int(self.action_timeout * 1000))
        elif action_type == "type":
            if not selector:
                raise BrowserActionError("type requires selector")
            page.locator(selector).fill(str(action.get("text", "")), timeout=int(self.action_timeout * 1000))
        elif action_type == "wait_for":
            if not selector:
                raise BrowserActionError("wait_for requires selector")
            page.locator(selector).wait_for(state=str(action.get("state", "visible")), timeout=int(self.action_timeout * 1000))
        elif action_type == "scroll":
            if selector:
                page.locator(selector).scroll_into_view_if_needed(timeout=int(self.action_timeout * 1000))
            else:
                amount = int(action.get("amount", 700))
                page.mouse.wheel(0, amount)
        elif action_type == "extract":
            target = page.locator(selector or "body")
            extracted = {"selector": selector or "body", "text": target.inner_text(timeout=int(self.action_timeout * 1000))}
            attribute = action.get("attribute")
            if attribute:
                extracted["attribute"] = attribute
                extracted["value"] = target.get_attribute(str(attribute), timeout=int(self.action_timeout * 1000))
            self._extracted_for_page(page).append(extracted)
        else:
            raise BrowserActionError(f"unsupported browser action: {action_type}")

    @staticmethod
    def _extracted_for_page(page) -> list[dict]:
        values = getattr(page, "_agentweb_extracted", None)
        if values is None:
            values = []
            setattr(page, "_agentweb_extracted", values)
        return values
