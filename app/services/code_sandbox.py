"""Docker-backed untrusted-code runner with a deny-by-default container profile.

The host must provide a pinned, prebuilt image. The runner never pulls images,
mounts the Docker socket, grants network access, or exposes host secrets.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class SandboxError(RuntimeError):
    pass


class DockerSandbox:
    def __init__(self, *, image: str, docker_binary: str = "docker",
                 timeout_seconds: int = 60, memory: str = "256m",
                 cpus: str = "1.0", pids_limit: int = 64,
                 max_source_bytes: int = 256_000):
        if not image or image.endswith(":latest") or "@sha256:" not in image:
            raise ValueError("sandbox image must be pinned by immutable sha256 digest")
        if not 1 <= timeout_seconds <= 300 or not 1 <= pids_limit <= 256:
            raise ValueError("sandbox resource limits are outside permitted bounds")
        if not re.fullmatch(r"[0-9]+m", memory) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", cpus):
            raise ValueError("invalid sandbox resource limit")
        self.image, self.docker_binary = image, docker_binary
        self.timeout_seconds, self.memory, self.cpus = timeout_seconds, memory, cpus
        self.pids_limit, self.max_source_bytes = pids_limit, max_source_bytes

    def run_python(self, source: str) -> dict:
        if not isinstance(source, str) or not source.strip():
            raise SandboxError("source is required")
        encoded = source.encode("utf-8")
        if len(encoded) > self.max_source_bytes:
            raise SandboxError("source exceeds configured limit")
        docker = shutil.which(self.docker_binary)
        if docker is None:
            raise SandboxError("container runtime is unavailable")
        with tempfile.TemporaryDirectory(prefix="nexus-sandbox-") as directory:
            workspace = Path(directory)
            source_file = workspace / "main.py"
            source_file.write_bytes(encoded)
            os.chmod(source_file, 0o400)
            command = [
                docker, "run", "--rm", "--pull=never",
                "--network=none", "--read-only",
                "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--pids-limit", str(self.pids_limit),
                "--memory", self.memory, "--cpus", self.cpus,
                "--user", "65534:65534",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--mount", f"type=bind,src={source_file},dst=/workspace/main.py,readonly",
                "--workdir", "/workspace",
                self.image, "python", "-I", "/workspace/main.py",
            ]
            try:
                result = subprocess.run(command, capture_output=True, text=True,
                                         timeout=self.timeout_seconds, check=False,
                                         env={"PATH": os.path.dirname(docker)})
            except subprocess.TimeoutExpired as exc:
                raise SandboxError("sandbox execution timed out") from exc
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout[-16_384:],
                "stderr": result.stderr[-16_384:],
                "timed_out": False,
                "network": "disabled",
                "image": self.image,
            }
