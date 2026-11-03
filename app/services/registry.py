class AgentRegistry:
    def __init__(self):
        self._agents = {
            "research": {"name": "Research Agent", "status": "registered", "permissions": ["research.read"]},
            "analysis": {"name": "Analysis Agent", "status": "registered", "permissions": ["analysis.run"]},
            "developer": {"name": "Developer Agent", "status": "registered", "permissions": ["code.propose"]},
            "executor": {"name": "Execution Agent", "status": "registered", "permissions": ["task.execute.low_risk"]},
            "auditor": {"name": "Auditor Agent", "status": "registered", "permissions": ["audit.read"]},
        }

    def list_agents(self):
        return [{"id": key, **value} for key, value in self._agents.items()]

    def get(self, agent_id):
        return self._agents.get(agent_id)
