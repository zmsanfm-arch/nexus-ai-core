import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from app.services.browser_test import BrowserTestError, PlaywrightLocalTester


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"""<!doctype html><html><head><title>NEXUS fixture</title></head>
        <body><main><h1 id='heading'>Local browser fixture</h1></main></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


@pytest.fixture
def fixture_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_browser_tester_rejects_non_loopback_targets(tmp_path):
    tester = PlaywrightLocalTester()
    with pytest.raises(BrowserTestError, match="loopback"):
        tester.inspect("https://example.com", tmp_path)


def test_browser_tester_captures_local_fixture_at_three_viewports(tmp_path, fixture_url):
    pytest.importorskip("playwright")
    tester = PlaywrightLocalTester()
    output_root = Path(os.getenv("NEXUS_BROWSER_ARTIFACT_DIR", str(tmp_path))).resolve()
    viewports = {"mobile": (390, 844), "tablet": (768, 1024), "desktop": (1365, 900)}
    for name, viewport in viewports.items():
        report = tester.inspect(fixture_url, output_root / name, viewport=viewport)
        assert report["passed"] is True
        assert report["title"] == "NEXUS fixture"
        assert report["blocked_external_requests"] == []
        assert (output_root / name / "browser-check.png").is_file()
