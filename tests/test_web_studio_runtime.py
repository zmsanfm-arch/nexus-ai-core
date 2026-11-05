import subprocess
from pathlib import Path

import pytest

from app.services.web_studio_runtime import (
    BrowserTesterHandler, OfflineDockerBuild, WebRuntimeError,
)
from app.services.specialist_contract import SpecialistInput


IMAGE = "registry.local/python@sha256:" + "a" * 64


def test_offline_build_requires_digest_pinned_allowlisted_base():
    with pytest.raises(ValueError, match="digest-pinned"):
        OfflineDockerBuild(base_image_allowlist={"python:3.12"})


def test_build_rejects_unpinned_or_unapproved_from(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    builder = OfflineDockerBuild(base_image_allowlist={IMAGE})
    with pytest.raises(WebRuntimeError, match="digest-pinned"):
        builder.build(tmp_path)


def test_build_command_is_network_isolated_and_never_pulls(tmp_path, monkeypatch):
    (tmp_path / "Dockerfile").write_text(f"FROM {IMAGE}\n")
    (tmp_path / "index.html").write_text("ok")
    calls = []
    monkeypatch.setattr("app.services.web_studio_runtime.shutil.which", lambda _: "/usr/bin/docker")
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "built", "")
    monkeypatch.setattr("app.services.web_studio_runtime.subprocess.run", fake_run)
    result = OfflineDockerBuild(base_image_allowlist={IMAGE}).build(tmp_path)
    command, kwargs = calls[0]
    assert result["success"] is True
    assert "--network=none" in command
    assert "--pull=false" in command
    assert "--no-cache" in command
    assert kwargs["timeout"] == 300
    assert kwargs["env"]["DOCKER_BUILDKIT"] == "1"


def test_build_rejects_symlink_and_sensitive_context(tmp_path):
    (tmp_path / "Dockerfile").write_text(f"FROM {IMAGE}\n")
    (tmp_path / ".env").write_text("SECRET=x")
    builder = OfflineDockerBuild(base_image_allowlist={IMAGE})
    with pytest.raises(WebRuntimeError, match="sensitive"):
        builder.build(tmp_path)


def test_browser_tester_persists_report_and_screenshot():
    class Store:
        def __init__(self):
            self.items = []
        def put(self, principal, content, **kwargs):
            record = {"artifact_id": str(len(self.items)), "size_bytes": len(content), **kwargs}
            self.items.append((principal, content, record))
            return record
    store = Store()
    handler = BrowserTesterHandler(
        runner=lambda _: {"report": {"passed": 2}, "screenshots": [
            {"name": "desktop", "content": b"PNG", "media_type": "image/png",
             "viewport": "1440x900"}]},
        artifact_store=store,
    )
    request = SpecialistInput(task_id="run_1", task_type="web.browser.test",
        request="Test website", context={"principal_id": "user-1", "mission_id": "site-1"})
    result = handler.run(request)
    assert result.agent_id == "web_browser_tester"
    assert len(store.items) == 2
    assert all(item[0] == "user-1" for item in store.items)
    assert store.items[0][2]["metadata"]["kind"] == "browser_screenshot"
    assert store.items[1][2]["metadata"]["kind"] == "browser_test_report"


def test_browser_tester_rejects_missing_principal():
    handler = BrowserTesterHandler(runner=lambda _: {"report": {}, "screenshots": []},
                                   artifact_store=object())
    request = SpecialistInput(task_id="run_1", task_type="web.browser.test",
                              request="Test website")
    with pytest.raises(WebRuntimeError, match="principal"):
        handler.run(request)

def test_all_web_studio_capabilities_have_central_permissions():
    from app.services.permissions import CAPABILITY_PERMISSIONS, CORE_ALLOWED_PERMISSIONS
    expected = {
        "web.mission.orchestrate", "web.brief.analyze", "web.research.public",
        "web.ux.architecture", "web.ui.design", "web.visual.identity",
        "web.motion.design", "web.content.plan", "web.seo.audit",
        "web.frontend.build", "web.backend.build", "web.cms.integrate",
        "web.accessibility.audit", "web.browser.test", "web.visual.audit",
        "web.performance.audit", "web.security.audit", "web.conversion.analyze",
        "web.release.prepare", "web.quality.audit", "web.maintenance.review",
    }
    assert expected <= set(CAPABILITY_PERMISSIONS)
    assert {CAPABILITY_PERMISSIONS[key] for key in expected} <= CORE_ALLOWED_PERMISSIONS
