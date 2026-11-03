from pathlib import Path

from app.services.manifest_loader import ManifestError, load_manifest


class AgentRegistry:
    def __init__(self, manifest_dirs=None):
        self._agents = {
            "research": {"name": "Research Agent", "status": "registered", "permissions": ["research.read"]},
            "analysis": {"name": "Analysis Agent", "status": "registered", "permissions": ["analysis.run"]},
            "developer": {"name": "Developer Agent", "status": "registered", "permissions": ["code.propose"]},
            "executor": {"name": "Execution Agent", "status": "registered", "permissions": ["task.execute.low_risk"]},
            "auditor": {"name": "Auditor Agent", "status": "registered", "permissions": ["audit.read"]},
        }
        if manifest_dirs is None:
            manifest_dirs = [Path(__file__).resolve().parents[2] / "agents"]
        self._load_manifests(manifest_dirs)

    def _load_manifests(self, manifest_dirs):
        for directory in manifest_dirs:
            root = Path(directory)
            if not root.exists():
                continue
            for manifest_path in sorted(root.glob("*/agent.yaml")):
                manifest = load_manifest(manifest_path)
                if manifest.agent_id in self._agents:
                    raise ManifestError(
                        f"Duplicate agent id in manifest: {manifest.agent_id}"
                    )
                self._agents[manifest.agent_id] = {
                    "name": manifest.name,
                    "version": manifest.version,
                    "status": manifest.status,
                    "mode": manifest.mode,
                    "capabilities": list(manifest.capabilities),
                    "permissions": list(manifest.permissions),
                    "requested_permissions": list(manifest.requested_permissions),
                }

    def list_agents(self):
        return [{"id": key, **value} for key, value in self._agents.items()]

    def get(self, agent_id):
        return self._agents.get(agent_id)

    def resolve_capability(self, capability):
        """Return only enabled registrations; disabled specialists fail closed."""
        matches = []
        for agent_id, spec in self._agents.items():
            if spec.get("status") != "registered":
                continue
            if capability in spec.get("capabilities", []):
                matches.append({"id": agent_id, **spec})
        return matches
