"""Secure Web Studio adapters: offline Docker builds and mission-scoped browser evidence.

The browser runner is injected by the deployment image (normally Playwright).
This module owns validation and artifact persistence, not browser installation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Callable, Any

from app.services.specialist_contract import SpecialistInput, SpecialistResult


class WebRuntimeError(RuntimeError):
    pass


class OfflineDockerBuild:
    """Build an uploaded website context with Docker's network disabled.

    Base images must already exist locally and be digest-pinned. The service
    never pulls, pushes, or starts the resulting image.
    """

    def __init__(self, *, base_image_allowlist: set[str], docker_binary: str = "docker",
                 timeout_seconds: int = 300, max_context_bytes: int = 25_000_000,
                 memory: str = "1g", cpus: str = "1.5"):
        if not 1 <= timeout_seconds <= 900:
            raise ValueError("timeout_seconds outside allowed range")
        if not re.fullmatch(r"[0-9]+(?:m|g)", memory) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", cpus):
            raise ValueError("invalid Docker resource limits")
        if not base_image_allowlist or any("@sha256:" not in x for x in base_image_allowlist):
            raise ValueError("base image allowlist must contain digest-pinned images")
        self.base_image_allowlist = frozenset(base_image_allowlist)
        self.docker_binary = docker_binary
        self.timeout_seconds = timeout_seconds
        self.max_context_bytes = max_context_bytes
        self.memory, self.cpus = memory, cpus

    def _validate_context(self, root: Path) -> tuple[list[Path], int]:
        if not root.is_dir() or root.is_symlink():
            raise WebRuntimeError("build context must be a real directory")
        dockerfile = root / "Dockerfile"
        if not dockerfile.is_file() or dockerfile.is_symlink():
            raise WebRuntimeError("build context requires a regular Dockerfile")
        docker_text = dockerfile.read_text(encoding="utf-8")
        from_images = []
        for line in docker_text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and re.match(r"(?i)^FROM\s+", stripped):
                parts = stripped.split()
                image = next((part for part in parts[1:] if not part.startswith("--")), "")
                if not image or image.lower() == "as" or "@sha256:" not in image:
                    raise WebRuntimeError("every FROM image must be digest-pinned")
                from_images.append(image)
        if not from_images or any(image not in self.base_image_allowlist for image in from_images):
            raise WebRuntimeError("Dockerfile references a base image outside the local allowlist")
        files, total = [], 0
        for item in root.rglob("*"):
            if item.is_symlink():
                raise WebRuntimeError("symlinks are forbidden in build contexts")
            if item.is_file():
                relative = item.relative_to(root)
                if ".." in PurePosixPath(relative.as_posix()).parts:
                    raise WebRuntimeError("invalid build context path")
                total += item.stat().st_size
                if total > self.max_context_bytes:
                    raise WebRuntimeError("build context exceeds configured size limit")
                if any(part == ".git" or part == "secrets" or part.startswith(".env") for part in relative.parts):
                    raise WebRuntimeError("sensitive paths are forbidden in build context")
                files.append(item)
        return files, total

    def build(self, context_dir: str | Path) -> dict[str, Any]:
        supplied_root = Path(context_dir).expanduser()
        if supplied_root.is_symlink():
            raise WebRuntimeError("build context must not be a symlink")
        root = supplied_root.resolve()
        files, context_size = self._validate_context(root)
        docker = shutil.which(self.docker_binary)
        if not docker:
            raise WebRuntimeError("Docker CLI is unavailable")
        tag = "nexus-web-build:" + hashlib.sha256(os.urandom(32)).hexdigest()[:20]
        with tempfile.TemporaryDirectory(prefix="nexus-web-context-") as temp:
            archive = Path(temp) / "context.tar"
            with tarfile.open(archive, "w") as tar:
                for item in files:
                    tar.add(item, arcname=item.relative_to(root).as_posix(), recursive=False)
            command = [
                docker, "build", "--network=none", "--pull=false", "--no-cache",
                "--memory", self.memory, "--cpu-period", "100000",
                "--cpu-quota", str(int(float(self.cpus) * 100000)),
                "--tag", tag, "-",
            ]
            try:
                result = subprocess.run(command, input=archive.read_bytes(), capture_output=True, text=False,
                                         timeout=self.timeout_seconds, check=False,
                                         env={"PATH": os.path.dirname(docker), "DOCKER_BUILDKIT": "1"})
            except subprocess.TimeoutExpired as exc:
                raise WebRuntimeError("Docker build timed out") from exc
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "image_tag": tag if result.returncode == 0 else None,
                "context_size_bytes": context_size,
                "network": "disabled",
                "pull": "disabled",
                "stdout": (result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else result.stdout)[-12000:],
                "stderr": (result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else result.stderr)[-12000:],
            }


class BrowserTesterHandler:
    """Run a trusted browser adapter and persist its report and screenshots.

    runner(request) must return {report: dict, screenshots: [{name, content,
    media_type, viewport}]} where content is bytes. The runner itself must
    execute in a disposable browser container with restricted egress.
    """

    agent_id = "web_browser_tester"

    def __init__(self, *, runner: Callable[[SpecialistInput], dict], artifact_store,
                 max_screenshots: int = 20, max_screenshot_bytes: int = 5_000_000):
        self.runner = runner
        self.artifact_store = artifact_store
        self.max_screenshots = max_screenshots
        self.max_screenshot_bytes = max_screenshot_bytes

    def run(self, request: SpecialistInput) -> SpecialistResult:
        principal_id = request.context.get("principal_id")
        mission_id = request.context.get("mission_id")
        if not isinstance(principal_id, str) or not principal_id or not isinstance(mission_id, str):
            raise WebRuntimeError("mission principal and mission id are required")
        result = self.runner(request)
        if not isinstance(result, dict) or not isinstance(result.get("report"), dict):
            raise WebRuntimeError("browser runner returned an invalid report")
        screenshots = result.get("screenshots", [])
        if not isinstance(screenshots, list) or len(screenshots) > self.max_screenshots:
            raise WebRuntimeError("browser screenshot count exceeds limit")
        saved = []
        for shot in screenshots:
            if not isinstance(shot, dict) or not isinstance(shot.get("content"), bytes):
                raise WebRuntimeError("invalid screenshot payload")
            content = shot["content"]
            media_type = shot.get("media_type")
            if media_type not in {"image/png", "image/jpeg", "image/webp"}:
                raise WebRuntimeError("unsupported screenshot media type")
            if len(content) > self.max_screenshot_bytes:
                raise WebRuntimeError("screenshot exceeds configured size limit")
            record = self.artifact_store.put(
                principal_id, content, media_type=media_type, mission_id=mission_id,
                metadata={"kind": "browser_screenshot", "name": str(shot.get("name", "screenshot"))[:128],
                          "viewport": shot.get("viewport")},
            )
            saved.append(record)
        report_bytes = json.dumps(result["report"], ensure_ascii=False, separators=(",", ":")).encode()
        report = self.artifact_store.put(
            principal_id, report_bytes, media_type="application/json", mission_id=mission_id,
            metadata={"kind": "browser_test_report", "screenshot_count": len(saved)},
        )
        answer = json.dumps({"report_artifact": report, "screenshots": saved},
                            ensure_ascii=False, separators=(",", ":"))
        return SpecialistResult(
            agent_id=self.agent_id, mode="advisory", answer=answer,
            source_claims=[], user_rules_used=[], agent_inferences=[], proposed_actions=[],
            risk_decision="not_requested", execution_result=None, uncertainties=[],
        )
