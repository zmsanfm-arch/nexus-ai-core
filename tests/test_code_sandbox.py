import subprocess

import pytest

from app.services.code_sandbox import DockerSandbox, SandboxError


def test_sandbox_requires_digest_pinned_image():
    with pytest.raises(ValueError, match="sha256"):
        DockerSandbox(image="python:3.12")


def test_sandbox_command_disables_network_and_privileges(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("app.services.code_sandbox.shutil.which", lambda _: "/usr/bin/docker")
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "ok", "")
    monkeypatch.setattr("app.services.code_sandbox.subprocess.run", fake_run)
    runner = DockerSandbox(image="registry.example/python@sha256:" + "a" * 64)
    result = runner.run_python("print('safe')")
    command, kwargs = calls[0]
    assert result["exit_code"] == 0
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert kwargs["timeout"] == 60
    assert kwargs["env"].keys() == {"PATH"}


def test_sandbox_rejects_large_source():
    runner = DockerSandbox(image="registry.example/python@sha256:" + "b" * 64,
                           max_source_bytes=4)
    with pytest.raises(SandboxError, match="limit"):
        runner.run_python("print('too long')")


def test_sandbox_timeout_is_reported(monkeypatch):
    monkeypatch.setattr("app.services.code_sandbox.shutil.which", lambda _: "/usr/bin/docker")
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr("app.services.code_sandbox.subprocess.run", timeout)
    runner = DockerSandbox(image="registry.example/python@sha256:" + "c" * 64)
    with pytest.raises(SandboxError, match="timed out"):
        runner.run_python("while True: pass")
