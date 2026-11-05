"""Playwright runner in a disposable, egress-gateway-only Docker network.

The browser network must be Docker-internal. Its only route to the Internet is
a separately hardened egress proxy attached to this internal network and an
external network. The proxy must enforce host allowlists and deny private,
loopback, link-local, multicast and reserved IP ranges after DNS resolution.
"""
from __future__ import annotations

import base64
import ipaddress
import json
import os
import re
import shutil
import subprocess
from urllib.parse import urlsplit

from app.services.web_studio_runtime import WebRuntimeError


_BROWSER_SCRIPT = r'''
import base64, json, sys
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

payload = json.load(sys.stdin)
allowed = {str(x).lower().rstrip(".") for x in payload["allowed_domains"]}
target = payload["target_url"]
proxy = payload["proxy"]
max_seconds = int(payload["timeout_seconds"])
screenshots = []
console_errors = []
page_errors = []
responses = []

def allowed_url(value):
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme == "https" and any(
            host == domain or host.endswith("." + domain) for domain in allowed
        )
    except Exception:
        return False

if not allowed_url(target):
    raise RuntimeError("target URL is outside the approved HTTPS domain allowlist")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy={"server": proxy},
        args=[
            "--proxy-bypass-list=<-loopback>",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-features=MediaRouter,OptimizationHints,Translate",
            "--disable-webrtc",
        ],
    )
    context = browser.new_context(
        ignore_https_errors=False,
        service_workers="block",
        accept_downloads=False,
        viewport={"width": 1365, "height": 900},
    )
    page = context.new_page()
    page.set_default_timeout(min(max_seconds * 1000, 60000))
    page.on("console", lambda msg: console_errors.append(msg.text[:500]) if msg.type == "error" else None)
    page.on("pageerror", lambda err: page_errors.append(str(err)[:500]))
    page.on("response", lambda response: responses.append({
        "url": response.url[:1000], "status": response.status
    }) if len(responses) < 200 else None)

    def guard(route):
        if not allowed_url(route.request.url):
            route.abort("blockedbyclient")
        else:
            route.continue_()

    page.route("**/*", guard)
    page.goto(target, wait_until="domcontentloaded", timeout=min(max_seconds * 1000, 60000))
    page.wait_for_timeout(500)
    shot = page.screenshot(type="png", full_page=True, animations="disabled")
    screenshots.append({
        "name": "desktop", "media_type": "image/png",
        "content": base64.b64encode(shot).decode("ascii"),
        "viewport": "1365x900",
    })
    report = {
        "target_url": target,
        "final_url": page.url,
        "title": page.title(),
        "status": "completed",
        "console_errors": console_errors[:100],
        "page_errors": page_errors[:100],
        "responses": responses,
        "checks": {"navigation": True, "screenshot": True, "request_allowlist": True},
    }
    context.close()
    browser.close()

print(json.dumps({"report": report, "screenshots": screenshots}, separators=(",", ":")))
'''


class PlaywrightDockerRunner:
    """Run a bounded Playwright smoke test behind an internal egress gateway."""

    def __init__(
        self, *, image: str, network: str, proxy_url: str,
        proxy_container: str, allowed_domains: set[str] | list[str], docker_binary: str = "docker",
        timeout_seconds: int = 90, memory: str = "1g", cpus: str = "2",
    ):
        if not (re.fullmatch(r".+@sha256:[a-f0-9]{64}", image) or re.fullmatch(r"sha256:[a-f0-9]{64}", image)):
            raise ValueError("Playwright image must be digest-pinned")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", network):
            raise ValueError("invalid browser network name")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", proxy_container):
            raise ValueError("invalid egress proxy container name")
        parsed_proxy = urlsplit(proxy_url)
        if parsed_proxy.scheme != "http" or parsed_proxy.hostname != proxy_container or parsed_proxy.username or parsed_proxy.password:
            raise ValueError("egress proxy URL must resolve to the configured internal proxy container")
        if not 5 <= timeout_seconds <= 180:
            raise ValueError("browser timeout outside permitted range")
        if not re.fullmatch(r"[0-9]+(?:m|g)", memory) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", cpus):
            raise ValueError("invalid browser resource limits")
        normalized_domains = {str(x).lower().rstrip(".") for x in allowed_domains}
        if not normalized_domains or any(
            not re.fullmatch(r"[a-z0-9.-]{1,253}", domain) or ".." in domain
            for domain in normalized_domains
        ):
            raise ValueError("browser domain allowlist is invalid")
        for domain in normalized_domains:
            try:
                ipaddress.ip_address(domain)
            except ValueError:
                continue
            raise ValueError("browser allowlist must contain DNS names, not IP literals")
        self.allowed_domains = frozenset(normalized_domains)
        self.image, self.network, self.proxy_url = image, network, proxy_url
        self.proxy_container, self.docker_binary = proxy_container, docker_binary
        self.timeout_seconds, self.memory, self.cpus = timeout_seconds, memory, cpus

    def _docker(self, args, *, timeout=10):
        binary = shutil.which(self.docker_binary)
        if not binary:
            raise WebRuntimeError("Docker CLI is unavailable")
        result = subprocess.run(
            [binary, *args], capture_output=True, text=True,
            timeout=timeout, check=False,
            env={"PATH": os.path.dirname(binary)},
        )
        if result.returncode:
            raise WebRuntimeError("Docker browser isolation preflight failed.")
        return result.stdout.strip()

    def _verify_network(self):
        internal = self._docker([
            "network", "inspect", self.network,
            "--format", "{{.Internal}}",
        ])
        if internal.lower() != "true":
            raise WebRuntimeError("browser Docker network must be internal")
        raw = self._docker([
            "inspect", self.proxy_container,
            "--format", "{{json .NetworkSettings.Networks}}",
        ])
        try:
            networks = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise WebRuntimeError("egress proxy network membership is invalid") from exc
        if self.network not in networks or len(networks) != 2:
            raise WebRuntimeError("egress proxy must join only the internal browser network and one egress network")
        external_network = next(name for name in networks if name != self.network)
        if self._docker([
            "network", "inspect", external_network, "--format", "{{.Internal}}",
        ]).lower() != "false":
            raise WebRuntimeError("egress proxy outbound network must not be internal")
        raw_members = self._docker([
            "network", "inspect", self.network,
            "--format", "{{json .Containers}}",
        ])
        try:
            members = json.loads(raw_members or "{}")
            member_names = {item.get("Name") for item in members.values()}
        except (TypeError, ValueError, AttributeError) as exc:
            raise WebRuntimeError("browser network membership is invalid") from exc
        if member_names != {self.proxy_container}:
            raise WebRuntimeError("only the approved egress proxy may join the browser network")
        raw_env = self._docker([
            "inspect", self.proxy_container,
            "--format", "{{json .Config.Env}}",
        ])
        try:
            env_items = json.loads(raw_env)
            proxy_env = dict(item.split("=", 1) for item in env_items if "=" in item)
            if proxy_env.get("NEXUS_EGRESS_PROXY_MODE") != "allowlist-v1":
                raise ValueError("proxy mode missing")
            proxy_domains = {
                item.strip().lower().rstrip(".")
                for item in proxy_env.get("NEXUS_EGRESS_ALLOWED_DOMAINS", "").split(",")
                if item.strip()
            }
            if not proxy_domains:
                raise ValueError("proxy allowlist missing")
        except (TypeError, ValueError) as exc:
            raise WebRuntimeError("egress proxy allowlist configuration is not verified") from exc
        raw_labels = self._docker([
            "inspect", self.proxy_container,
            "--format", "{{json .Config.Labels}}",
        ])
        try:
            labels = json.loads(raw_labels)
        except (TypeError, ValueError) as exc:
            raise WebRuntimeError("egress proxy image identity is not verified") from exc
        if labels.get("com.nexus.component") != "browser-egress-proxy" or labels.get("com.nexus.egress-policy") != "allowlist-v1":
            raise WebRuntimeError("egress proxy image is not an approved NEXUS gateway")
        return proxy_domains

    @staticmethod
    def _validate_target(target, allowed_domains):
        if not isinstance(target, str) or len(target) > 2048:
            raise WebRuntimeError("browser target URL is missing or too long")
        parsed = urlsplit(target)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise WebRuntimeError("browser target must be an HTTPS URL without credentials")
        try:
            ipaddress.ip_address(host)
            raise WebRuntimeError("IP-literal browser targets are forbidden; use an approved DNS name")
        except ValueError:
            pass
        if not isinstance(allowed_domains, list) or not allowed_domains:
            raise WebRuntimeError("trusted browser domain allowlist is required")
        normalized = {str(x).lower().rstrip(".") for x in allowed_domains}
        if any(not re.fullmatch(r"[a-z0-9.-]{1,253}", d) or ".." in d for d in normalized):
            raise WebRuntimeError("invalid browser domain allowlist")
        if not any(host == d or host.endswith("." + d) for d in normalized):
            raise WebRuntimeError("browser target is outside the approved domain allowlist")
        return normalized

    def __call__(self, request):
        context = request.context or {}
        target = context.get("browser_target_url")
        if not target:
            match = re.search(r"https://[A-Za-z0-9.-]+(?::443)?(?:/[^\\s]*)?", request.request)
            target = match.group(0).rstrip(".,;)]}") if match else None
        allowed = self._validate_target(target, sorted(self.allowed_domains))
        proxy_domains = self._verify_network()
        if not allowed.issubset(proxy_domains):
            raise WebRuntimeError("mission domain allowlist exceeds the egress proxy allowlist")
        self._docker(["image", "inspect", self.image])
        payload = {
            "target_url": target,
            "allowed_domains": sorted(allowed),
            "proxy": self.proxy_url,
            "timeout_seconds": self.timeout_seconds,
        }
        command = [
            self.docker_binary, "run", "--rm",
            "--network", self.network,
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--pids-limit", "128",
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--shm-size", "256m",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
            "--user", "1000:1000",
            "--env", "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright",
            "--env", "HOME=/tmp",
            "--entrypoint", "python",
            self.image, "-c", _BROWSER_SCRIPT,
        ]
        binary = shutil.which(self.docker_binary)
        if not binary:
            raise WebRuntimeError("Docker CLI is unavailable")
        try:
            result = subprocess.run(
                [binary, *command[1:]],
                input=json.dumps(payload, separators=(",", ":")),
                capture_output=True, text=True, timeout=self.timeout_seconds + 30,
                check=False, env={"PATH": os.path.dirname(binary)},
            )
        except subprocess.TimeoutExpired as exc:
            raise WebRuntimeError("isolated browser execution timed out") from exc
        if result.returncode:
            raise WebRuntimeError("isolated browser execution failed")
        try:
            output = json.loads(result.stdout)
            report = output["report"]
            raw_shots = output["screenshots"]
            if not isinstance(report, dict) or not isinstance(raw_shots, list):
                raise ValueError("invalid output")
            shots = []
            for shot in raw_shots[:5]:
                content = base64.b64decode(shot["content"], validate=True)
                shots.append({
                    "name": shot["name"], "media_type": shot["media_type"],
                    "content": content, "viewport": shot.get("viewport"),
                })
            return {"report": report, "screenshots": shots}
        except (KeyError, TypeError, ValueError) as exc:
            raise WebRuntimeError("isolated browser returned an invalid result") from exc


def playwright_runner_from_env():
    """Return None until the operator supplies a complete, pinned browser runtime."""
    image = os.getenv("NEXUS_PLAYWRIGHT_IMAGE", "").strip()
    network = os.getenv("NEXUS_BROWSER_INTERNAL_NETWORK", "").strip()
    proxy = os.getenv("NEXUS_BROWSER_EGRESS_PROXY_URL", "").strip()
    proxy_container = os.getenv("NEXUS_BROWSER_EGRESS_PROXY_CONTAINER", "").strip()
    allowed_domains = {
        item.strip().lower().rstrip(".")
        for item in os.getenv("NEXUS_BROWSER_ALLOWED_DOMAINS", "").split(",")
        if item.strip()
    }
    if not all((image, network, proxy, proxy_container, allowed_domains)):
        return None
    return PlaywrightDockerRunner(
        image=image, network=network, proxy_url=proxy,
        proxy_container=proxy_container, allowed_domains=allowed_domains,
        timeout_seconds=int(os.getenv("NEXUS_BROWSER_TIMEOUT_SECONDS", "90")),
    )
