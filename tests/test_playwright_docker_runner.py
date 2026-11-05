import base64
import json
import subprocess

import pytest

from app.services.playwright_docker_runner import PlaywrightDockerRunner
from app.services.web_studio_runtime import WebRuntimeError
from app.services.specialist_contract import SpecialistInput


IMAGE = "mcr.microsoft.com/playwright/python@sha256:" + "a" * 64


def make_runner():
    return PlaywrightDockerRunner(
        image=IMAGE,
        network="nexus-browser-internal",
        proxy_url="http://nexus-egress-proxy:3128",
        proxy_container="nexus-egress-proxy", allowed_domains={"example.com"},
    )


def test_playwright_runner_requires_digest_pinned_image():
    with pytest.raises(ValueError, match="digest-pinned"):
        PlaywrightDockerRunner(
            image="mcr.microsoft.com/playwright/python:latest",
            network="nexus-browser-internal",
            proxy_url="http://nexus-egress-proxy:3128",
            proxy_container="nexus-egress-proxy", allowed_domains={"example.com"},
        )


def test_playwright_target_must_be_https_and_allowlisted():
    runner = make_runner()
    assert runner._validate_target(
        "https://shop.example.com/home", ["example.com"]
    ) == {"example.com"}
    with pytest.raises(WebRuntimeError, match="HTTPS"):
        runner._validate_target("http://example.com", ["example.com"])
    with pytest.raises(WebRuntimeError, match="allowlist"):
        runner._validate_target("https://example.net", ["example.com"])
    with pytest.raises(WebRuntimeError, match="IP-literal"):
        runner._validate_target("https://127.0.0.1", ["127.0.0.1"])
    with pytest.raises(WebRuntimeError, match="port 443"):
        runner._validate_target("https://example.com:444", ["example.com"])


def test_playwright_runner_fails_closed_without_trusted_policy():
    runner = make_runner()
    request = SpecialistInput(task_id="m1", task_type="web.browser.test", request="test")
    with pytest.raises(WebRuntimeError, match="target URL"):
        runner(request)


def test_playwright_runner_verifies_internal_proxy_only_network(monkeypatch):
    runner = make_runner()
    responses = iter([
        "true",
        json.dumps({"nexus-browser-internal-abc": {"Name": "nexus-egress-proxy"}, "bridge": {"Name": "nexus-egress-proxy", "Gateway": "172.18.0.1"}}),
        "true",
        "false",
        "bridge",
        json.dumps({"proxy-id": {"Name": "nexus-egress-proxy"}}),
        "default via 172.18.0.1 dev eth0",
        json.dumps({"proxy-id": {"Name": "nexus-egress-proxy"}}),
        json.dumps(["NEXUS_EGRESS_PROXY_MODE=allowlist-v1", "NEXUS_EGRESS_ALLOWED_DOMAINS=example.com,example.net"]),
        json.dumps({"com.nexus.component": "browser-egress-proxy", "com.nexus.egress-policy": "allowlist-v1"}),
        "healthy",
    ])
    monkeypatch.setattr(runner, "_docker", lambda args, timeout=10: next(responses))
    runner._verify_network("nexus-browser-internal-abc")


def test_playwright_runner_rejects_other_containers_on_browser_network(monkeypatch):
    runner = make_runner()
    responses = iter([
        "true",
        json.dumps({"nexus-browser-internal-abc": {"Name": "nexus-egress-proxy"}, "bridge": {"Name": "nexus-egress-proxy", "Gateway": "172.18.0.1"}}),
        "true",
        "false",
        "bridge",
        json.dumps({"proxy-id": {"Name": "nexus-egress-proxy"}}),
        "default via 172.18.0.1 dev eth0",
        json.dumps({
            "proxy-id": {"Name": "nexus-egress-proxy"},
            "other-id": {"Name": "untrusted-container"},
        }),
    ])
    monkeypatch.setattr(runner, "_docker", lambda args, timeout=10: next(responses))
    with pytest.raises(WebRuntimeError, match="only the approved egress proxy"):
        runner._verify_network("nexus-browser-internal-abc")


def test_playwright_runner_uses_hardened_container_and_parses_evidence(monkeypatch):
    runner = make_runner()
    monkeypatch.setattr(runner, "_verify_network", lambda _network: {"example.com"})
    docker_calls = []
    monkeypatch.setattr(runner, "_docker", lambda args, timeout=10: docker_calls.append(args) or "")
    monkeypatch.setattr("app.services.playwright_docker_runner.shutil.which", lambda _: "/usr/bin/docker")
    screenshot = base64.b64encode(b"png-data").decode()
    output = json.dumps({
        "report": {"status": "completed"},
        "screenshots": [{
            "name": "desktop", "media_type": "image/png",
            "content": screenshot, "viewport": "1365x900",
        }],
    })
    calls = []
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, output, "")
    monkeypatch.setattr("app.services.playwright_docker_runner.subprocess.run", fake_run)
    request = SpecialistInput(
        task_id="m1", task_type="web.browser.test", request="run",
        context={
            "browser_target_url": "https://example.com",
        },
    )
    result = runner(request)
    command, kwargs = calls[0]
    assert result["report"]["status"] == "completed"
    assert result["screenshots"][0]["content"] == b"png-data"
    assert "--network" in command and any(x.startswith("nexus-browser-internal-") for x in command)
    assert any(call[:3] == ["network", "create", "--internal"] for call in docker_calls)
    assert any(call[:2] == ["rm", "-f"] for call in docker_calls)
    assert any(call[:2] == ["network", "disconnect"] for call in docker_calls)
    assert any(call[:2] == ["network", "rm"] for call in docker_calls)
    assert "--name" in command
    assert "--read-only" in command
    assert "--cap-drop" in command and "ALL" in command
    assert "--security-opt" in command and "no-new-privileges:true" in command
    assert "--pids-limit" in command and "128" in command
    assert kwargs["timeout"] == 120


def test_real_playwright_container_uses_egress_gateway():
    import os
    image = os.getenv("NEXUS_TEST_PLAYWRIGHT_IMAGE")
    network = os.getenv("NEXUS_TEST_BROWSER_NETWORK")
    proxy_url = os.getenv("NEXUS_TEST_BROWSER_PROXY_URL")
    proxy_container = os.getenv("NEXUS_TEST_BROWSER_PROXY_CONTAINER")
    if not all((image, network, proxy_url, proxy_container)):
        pytest.skip("real isolated Playwright Docker integration is not configured")
    runner = PlaywrightDockerRunner(
        image=image, network=network, proxy_url=proxy_url,
        proxy_container=proxy_container, allowed_domains={"example.com"}, timeout_seconds=90,
    )
    request = SpecialistInput(
        task_id="browser-ci", task_type="web.browser.test", request="CI browser smoke test",
        context={"browser_target_url": "https://example.com"},
    )
    result = runner(request)
    assert result["report"]["status"] == "completed"
    assert result["report"]["checks"]["navigation"] is True
    assert result["screenshots"]
    assert result["screenshots"][0]["content"].startswith(b"\\x89PNG")


def test_playwright_runner_from_env_requires_mutual_tls_and_client_certificates(monkeypatch, tmp_path):
    from app.services.playwright_docker_runner import playwright_runner_from_env
    cert_dir = tmp_path / "docker-certs"
    cert_dir.mkdir()
    for name in ("ca.pem", "cert.pem", "key.pem"):
        (cert_dir / name).write_text("test-certificate")
    values = {
        "NEXUS_PLAYWRIGHT_IMAGE": IMAGE,
        "NEXUS_BROWSER_INTERNAL_NETWORK": "nexus-browser",
        "NEXUS_BROWSER_EGRESS_PROXY_URL": "http://nexus-egress-proxy:3128",
        "NEXUS_BROWSER_EGRESS_PROXY_CONTAINER": "nexus-egress-proxy",
        "NEXUS_BROWSER_ALLOWED_DOMAINS": "example.com",
        "NEXUS_BROWSER_DOCKER_HOST": "tcp://browser-host.internal:2376",
        "NEXUS_BROWSER_DOCKER_TLS_VERIFY": "1",
        "NEXUS_BROWSER_DOCKER_CERT_PATH": str(cert_dir),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    runner = playwright_runner_from_env()
    assert runner.docker_env["DOCKER_HOST"] == values["NEXUS_BROWSER_DOCKER_HOST"]
    assert runner.docker_env["DOCKER_TLS_VERIFY"] == "1"
    assert runner.docker_env["DOCKER_CERT_PATH"] == str(cert_dir)


def test_playwright_runner_from_env_rejects_plaintext_remote_docker(monkeypatch, tmp_path):
    from app.services.playwright_docker_runner import playwright_runner_from_env
    cert_dir = tmp_path / "docker-certs"
    cert_dir.mkdir()
    for name in ("ca.pem", "cert.pem", "key.pem"):
        (cert_dir / name).write_text("test-certificate")
    values = {
        "NEXUS_PLAYWRIGHT_IMAGE": IMAGE,
        "NEXUS_BROWSER_INTERNAL_NETWORK": "nexus-browser",
        "NEXUS_BROWSER_EGRESS_PROXY_URL": "http://nexus-egress-proxy:3128",
        "NEXUS_BROWSER_EGRESS_PROXY_CONTAINER": "nexus-egress-proxy",
        "NEXUS_BROWSER_ALLOWED_DOMAINS": "example.com",
        "NEXUS_BROWSER_DOCKER_HOST": "tcp://browser-host.internal:2375",
        "NEXUS_BROWSER_DOCKER_TLS_VERIFY": "0",
        "NEXUS_BROWSER_DOCKER_CERT_PATH": str(cert_dir),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="mutually authenticated TLS"):
        playwright_runner_from_env()
