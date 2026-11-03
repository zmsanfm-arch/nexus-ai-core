class AgentRegistry:
    """Static capability catalog only; entries are not runtime registrations."""
    def __init__(self):
        self._agents = {
            "ict_mentor": {"name": "ICT Mentor", "status": "specification", "permissions": ["knowledge.retrieve", "user_input.read", "chart_attachment.read"]},
            "research": {"name": "Research Agent", "status": "catalog_only", "permissions": []},
            "analysis": {"name": "Analysis Agent", "status": "catalog_only", "permissions": []},
            "developer": {"name": "Developer Agent", "status": "catalog_only", "permissions": []},
            "executor": {"name": "Execution Agent", "status": "disabled", "permissions": []},
            "auditor": {"name": "Auditor Agent", "status": "catalog_only", "permissions": []},
        }

    def list_agents(self):
        return [{"id": key, **value} for key, value in self._agents.items()]

    def get(self, agent_id):
        return self._agents.get(agent_id)
