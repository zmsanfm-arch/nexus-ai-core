"""Real browser -> mission worker -> principal-scoped evidence E2E gate."""
import json
import os

import pytest

from app.services.artifact_store import ArtifactNotFound, LocalArtifactStore
from app.services.mission_run_repository import MissionRunRepository
from app.services.mission_run_worker import MissionRunWorker
from app.services.permissions import PermissionService
from app.services.playwright_docker_runner import PlaywrightDockerRunner
from app.services.web_studio_runtime import BrowserTesterHandler
from app.storage import SQLAlchemyStore


class BrowserRegistry:
    def list_agents(self):
        return [{
            "id": "web_browser_tester",
            "status": "registered",
            "mode": "advisory",
            "capabilities": ["web.browser.test"],
            "permissions": ["browser.execute"],
        }]


def test_real_browser_mission_persists_principal_scoped_evidence(tmp_path):
    image = os.getenv("NEXUS_TEST_PLAYWRIGHT_IMAGE")
    network = os.getenv("NEXUS_TEST_BROWSER_NETWORK")
    proxy_url = os.getenv("NEXUS_TEST_BROWSER_PROXY_URL")
    proxy_container = os.getenv("NEXUS_TEST_BROWSER_PROXY_CONTAINER")
    if not all((image, network, proxy_url, proxy_container)):
        pytest.skip("real isolated browser mission E2E is not configured")

    runner = PlaywrightDockerRunner(
        image=image, network=network, proxy_url=proxy_url,
        proxy_container=proxy_container, allowed_domains={"example.com"},
        timeout_seconds=90,
    )
    artifact_root = tmp_path / "mission-artifacts"
    artifacts = LocalArtifactStore(artifact_root)
    handler = BrowserTesterHandler(runner=runner, artifact_store=artifacts)
    database = SQLAlchemyStore(f"sqlite:///{tmp_path / 'mission-e2e.db'}")
    try:
        repository = MissionRunRepository(database)
        mission = {
            "mission_id": "browser_e2e",
            "name": "Isolated browser E2E",
            "objective": "Test website https://example.com",
            "nodes": [{
                "node_id": "browser_test",
                "agent_id": "web_browser_tester",
                "capability": "web.browser.test",
                "dependencies": [],
                "max_attempts": 1,
            }],
            "max_total_attempts": 1,
            "approval_policy": "required_for_external_actions",
        }
        run = repository.enqueue(
            "browser_e2e", "principal-e2e", "ci-browser-e2e", mission
        )
        worker = MissionRunWorker(
            repository=repository,
            registry=BrowserRegistry(),
            handlers={"web_browser_tester": handler},
            storage=database,
            worker_id="browser-e2e-worker",
            permission_service=PermissionService(
                capability_permissions={"web.browser.test": "browser.execute"},
                allowed_permissions=frozenset({"browser.execute"}),
            ),
            artifact_store=artifacts,
        )
        assert worker.run_once() is True
        snapshot = repository.get(run["run_id"], "principal-e2e")
        assert snapshot["status"] == "nodes_succeeded"
        node = snapshot["nodes"][0]
        assert node["status"] == "completed"
        output_artifact = node["output"]["_artifact"]["artifact_id"]
        metadata, output_bytes = artifacts.get("principal-e2e", output_artifact)
        assert metadata["metadata"]["kind"] == "specialist_output"
        result = json.loads(output_bytes)
        browser_evidence = json.loads(result["answer"])
        report_id = browser_evidence["report_artifact"]["artifact_id"]
        screenshot_id = browser_evidence["screenshots"][0]["artifact_id"]
        report_meta, report_bytes = artifacts.get("principal-e2e", report_id)
        screenshot_meta, screenshot_bytes = artifacts.get("principal-e2e", screenshot_id)
        assert report_meta["metadata"]["kind"] == "browser_test_report"
        assert screenshot_meta["metadata"]["kind"] == "browser_screenshot"
        assert json.loads(report_bytes)["status"] == "completed"
        assert screenshot_bytes.startswith(b"\x89PNG")
        with pytest.raises(ArtifactNotFound):
            artifacts.get("different-principal", screenshot_id)

        principal_dir = next(artifact_root.iterdir())
        stored_kinds = {
            json.loads(path.read_text(encoding="utf-8"))["metadata"]["kind"]
            for path in principal_dir.glob("*.json")
        }
        assert "mission_final_report" in stored_kinds
    finally:
        database.close()
