"""Compile a complete 21-role Web Studio website mission.

The compiler creates a bounded DAG from the department's 21 registered advisory roles.
It requires the caller to supply each role's manifest-declared capability;
it never invents grants or invokes tools. Runtime authorization remains separate.
"""
from __future__ import annotations

from app.services.mission_contract import MissionDefinition, MissionNode, compile_mission


# Stable department graph. Independent design and engineering/review work is
# represented as DAG levels; the current mission runtime still executes
# sequentially and must not be described as parallel.
WEB_STUDIO_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "web_studio_orchestrator": (),
    "web_brief_analyst": ("web_studio_orchestrator",),
    "web_research_analyst": ("web_brief_analyst",),
    "web_ia_ux_architect": ("web_research_analyst",),
    "web_ui_designer": ("web_ia_ux_architect",),
    "web_brand_visual_designer": ("web_ia_ux_architect",),
    "web_motion_designer": ("web_ui_designer", "web_brand_visual_designer"),
    "web_content_strategist": ("web_ia_ux_architect",),
    "web_seo_specialist": ("web_content_strategist",),
    "web_frontend_engineer": (
        "web_ui_designer", "web_brand_visual_designer",
        "web_motion_designer", "web_content_strategist",
    ),
    "web_backend_engineer": ("web_ia_ux_architect",),
    "web_cms_integrator": ("web_content_strategist", "web_backend_engineer"),
    "web_accessibility_specialist": ("web_frontend_engineer",),
    "web_browser_tester": (
        "web_frontend_engineer", "web_backend_engineer", "web_cms_integrator",
    ),
    "web_visual_qa": ("web_browser_tester", "web_ui_designer"),
    "web_performance_engineer": ("web_browser_tester",),
    "web_security_reviewer": ("web_backend_engineer", "web_browser_tester"),
    "web_conversion_analyst": ("web_visual_qa", "web_seo_specialist"),
    "web_release_engineer": (
        "web_accessibility_specialist", "web_visual_qa",
        "web_performance_engineer", "web_security_reviewer",
        "web_conversion_analyst",
    ),
    "web_quality_auditor": ("web_release_engineer",),
    "web_maintenance_agent": ("web_quality_auditor",),
}


class WebStudioWorkflowError(ValueError):
    """Raised when the Web Studio role/capability contract is incomplete."""


def build_web_studio_mission(
    *,
    mission_id: str,
    objective: str,
    agent_capabilities: dict[str, tuple[str, ...] | list[str]],
) -> MissionDefinition:
    """Build the 21-role mission from actual manifest capabilities.

    The caller must pass capabilities read from the live registry. This function
    only compiles a plan and grants nothing. The normal runtime independently
    checks enabled status, central permissions, and installed handlers.
    """
    expected = set(WEB_STUDIO_DEPENDENCIES)
    supplied = set(agent_capabilities)
    missing_roles = sorted(expected - supplied)
    if missing_roles:
        raise WebStudioWorkflowError(
            "Missing Web Studio role capability declarations: "
            + ", ".join(missing_roles)
        )

    nodes = []
    for agent_id, dependencies in WEB_STUDIO_DEPENDENCIES.items():
        declared = tuple(agent_capabilities[agent_id])
        if len(declared) != 1 or not declared[0].startswith("web."):
            raise WebStudioWorkflowError(
                f"{agent_id} must declare exactly one web.* capability"
            )
        nodes.append(MissionNode(
            node_id=agent_id.removeprefix("web_"),
            agent_id=agent_id,
            capability=declared[0],
            dependencies=tuple(dep.removeprefix("web_") for dep in dependencies),
            max_attempts=1,
        ))

    mission = MissionDefinition(
        mission_id=mission_id,
        name="Autonomous Web Development Studio",
        objective=objective,
        nodes=tuple(nodes),
        max_total_attempts=len(nodes),
    )
    # Compilation validates the graph and all referenced identities. It is
    # deliberately not an execution call.
    compile_mission(mission, expected)
    return mission
