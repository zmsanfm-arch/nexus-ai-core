import pytest

from app.services.web_studio_workflow import (
    WEB_STUDIO_DEPENDENCIES,
    WebStudioWorkflowError,
    build_web_studio_mission,
)
from app.services.mission_contract import compile_mission


def capabilities():
    return {
        agent_id: [f"web.test_{agent_id.removeprefix('web_')}"]
        for agent_id in WEB_STUDIO_DEPENDENCIES
    }


def test_builds_complete_bounded_21_role_website_mission():
    mission = build_web_studio_mission(
        mission_id="website_build",
        objective="Build a responsive website from the approved brief.",
        agent_capabilities=capabilities(),
    )
    plan = compile_mission(mission, set(WEB_STUDIO_DEPENDENCIES))
    assert len(mission.nodes) == 21
    assert mission.max_total_attempts == 21
    assert plan.max_attempts == 21
    auditor = next(node for node in mission.nodes if node.node_id == "quality_auditor")
    assert auditor.agent_id == "web_quality_auditor"
    assert auditor.dependencies == ("release_engineer",)


def test_design_and_quality_work_are_dependency_gated():
    mission = build_web_studio_mission(
        mission_id="website_build",
        objective="Build a website.",
        agent_capabilities=capabilities(),
    )
    by_id = {node.agent_id: node for node in mission.nodes}
    assert set(by_id["web_ui_designer"].dependencies) == {"ia_ux_architect"}
    assert set(by_id["web_brand_visual_designer"].dependencies) == {"ia_ux_architect"}
    assert "visual_qa" in by_id["web_release_engineer"].dependencies
    assert "security_reviewer" in by_id["web_release_engineer"].dependencies
    assert by_id["web_maintenance_agent"].dependencies == ("quality_auditor",)


def test_missing_role_capability_contract_fails_closed():
    supplied = capabilities()
    supplied.pop("web_security_reviewer")
    with pytest.raises(WebStudioWorkflowError, match="web_security_reviewer"):
        build_web_studio_mission(
            mission_id="website_build",
            objective="Build a website.",
            agent_capabilities=supplied,
        )


def test_non_web_or_ambiguous_capability_fails_closed():
    supplied = capabilities()
    supplied["web_frontend_engineer"] = ["repository.write", "web.frontend"]
    with pytest.raises(WebStudioWorkflowError, match="exactly one web"):
        build_web_studio_mission(
            mission_id="website_build",
            objective="Build a website.",
            agent_capabilities=supplied,
        )
