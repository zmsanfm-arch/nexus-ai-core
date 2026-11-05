"""Local-fixture-only Playwright verification; external navigation is denied."""
from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlsplit


class BrowserTestError(RuntimeError):
    pass


def _loopback_origin(url: str):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
        host = parsed.hostname.lower()
        if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
            return None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return parsed.scheme, host, port
    except ValueError:
        return None


class PlaywrightLocalTester:
    """Runs a bounded browser check against one loopback origin only."""

    def __init__(self, *, timeout_ms: int = 10_000, max_screenshot_bytes: int = 5_000_000):
        if not 1_000 <= timeout_ms <= 30_000:
            raise ValueError("timeout_ms must be between 1000 and 30000")
        if not 100_000 <= max_screenshot_bytes <= 20_000_000:
            raise ValueError("invalid screenshot size limit")
        self.timeout_ms = timeout_ms
        self.max_screenshot_bytes = max_screenshot_bytes

    def inspect(self, url: str, output_dir: str | Path, *, viewport: tuple[int, int] = (1365, 900)) -> dict:
        allowed_origin = _loopback_origin(url)
        if allowed_origin is None:
            raise BrowserTestError("browser tester accepts loopback fixture URLs only")
        width, height = viewport
        if not (320 <= width <= 2560 and 480 <= height <= 2160):
            raise BrowserTestError("viewport is outside permitted bounds")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserTestError("install requirements-browser.txt to enable browser tests") from exc

        destination = Path(output_dir).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        screenshot = destination / "browser-check.png"
        console_errors: list[str] = []
        page_errors: list[str] = []
        failed_requests: list[str] = []
        blocked_requests: list[str] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": width, "height": height},
                                          accept_downloads=False, service_workers="block")
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            def guard(route):
                request_url = route.request.url
                if request_url.startswith(("data:", "blob:", "about:")):
                    route.continue_()
                elif _loopback_origin(request_url) == allowed_origin:
                    route.continue_()
                else:
                    blocked_requests.append(request_url[:512])
                    route.abort("blockedbyclient")

            page.route("**/*", guard)
            page.on("console", lambda message: console_errors.append(message.text[:512])
                    if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)[:512]))
            page.on("requestfailed", lambda request: failed_requests.append(request.url[:512]))
            try:
                response = page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
                page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
                title = page.title()
                status = response.status if response is not None else None
            except Exception as exc:
                raise BrowserTestError(f"local browser inspection failed: {type(exc).__name__}") from exc
            finally:
                context.close()
                browser.close()

        screenshot_size = screenshot.stat().st_size
        if screenshot_size > self.max_screenshot_bytes:
            screenshot.unlink(missing_ok=True)
            raise BrowserTestError("screenshot exceeds configured size limit")
        return {
            "url": url,
            "title": title,
            "http_status": status,
            "viewport": {"width": width, "height": height},
            "console_errors": console_errors[:50],
            "page_errors": page_errors[:50],
            "failed_requests": failed_requests[:50],
            "blocked_external_requests": blocked_requests[:50],
            "screenshot": str(screenshot),
            "screenshot_bytes": screenshot_size,
            "passed": status is not None and 200 <= status < 400
                      and not console_errors and not page_errors and not blocked_requests,
        }
