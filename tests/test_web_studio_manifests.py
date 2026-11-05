from app.services.registry import AgentRegistry


WEB_STUDIO_AGENT_IDS = {
    "web_studio_orchestrator",
    "web_brief_analyst",
    "web_research_analyst",
    "web_ia_ux_architect",
    "web_ui_designer",
    "web_brand_visual_designer",
    "web_motion_designer",
    "web_content_strategist",
    "web_seo_specialist",
    "web_accessibility_specialist",
    "web_frontend_engineer",
    "web_backend_engineer",
    "web_cms_integrator",
    "web_browser_tester",
    "web_visual_qa",
    "web_performance_engineer",
    "web_security_reviewer",
    "web_conversion_analyst",
    "web_release_engineer",
    "web_maintenance_agent",
    "web_quality_auditor",
}


def test_web_studio_roles_are_discoverable_but_disabled():
    registry = AgentRegistry()
    registered = {item["id"]: item for item in registry.list_agents()}
    assert WEB_STUDIO_AGENT_IDS <= registered.keys()
    for agent_id in WEB_STUDIO_AGENT_IDS:
        agent = registered[agent_id]
        assert agent["status"] == "disabled"
        assert agent["mode"] == "advisory"
        assert agent["permissions"] == []
        assert registry.resolve_capability(agent["capabilities"][0]) == []
