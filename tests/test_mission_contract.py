import pytest
from pydantic import ValidationError

from app.services.mission_contract import (
    MissionContractError,
    MissionDefinition,
    compile_mission,
)


def mission_payload():
    return {
        "mission_id": "youtube_channel",
        "name": "YouTube channel research workflow",
        "objective": "Research current video formats and propose a content plan.",
        "nodes": [
            {"node_id": "research", "agent_id": "research"},
            {
                "node_id": "analysis",
                "agent_id": "analysis",
                "dependencies": ["research"],
            },
            {
                "node_id": "audit",
                "agent_id": "auditor",
                "dependencies": ["analysis"],
            },
        ],
        "max_total_attempts": 3,
    }


def test_mission_compiles_to_dependency_order():
    mission = MissionDefinition.model_validate(mission_payload())
    plan = compile_mission(mission, {"research", "analysis", "auditor"})
    assert plan.levels == (("research",), ("analysis",), ("audit",))
    assert plan.max_attempts == 3


def test_mission_rejects_unknown_agents():
    mission = MissionDefinition.model_validate(mission_payload())
    with pytest.raises(MissionContractError, match="unregistered agents"):
        compile_mission(mission, {"research", "analysis"})


def test_mission_rejects_cycles_and_unknown_dependencies():
    payload = mission_payload()
    payload["nodes"] = [
        {"node_id": "research", "agent_id": "research", "dependencies": ["audit"]},
        {"node_id": "audit", "agent_id": "auditor", "dependencies": ["research"]},
    ]
    with pytest.raises(ValidationError, match="dependency cycle"):
        MissionDefinition.model_validate(payload)

    payload = mission_payload()
    payload["nodes"][1]["dependencies"] = ["not_declared"]
    with pytest.raises(ValidationError, match="unknown dependencies"):
        MissionDefinition.model_validate(payload)


def test_mission_enforces_total_attempt_budget_and_strict_schema():
    payload = mission_payload()
    payload["max_total_attempts"] = 2
    with pytest.raises(ValidationError, match="attempt budget"):
        MissionDefinition.model_validate(payload)

    payload = mission_payload()
    payload["allow_shell"] = True
    with pytest.raises(ValidationError):
        MissionDefinition.model_validate(payload)


def test_external_action_approval_policy_cannot_be_disabled():
    payload = mission_payload()
    payload["approval_policy"] = "automatic"
    with pytest.raises(ValidationError):
        MissionDefinition.model_validate(payload)
