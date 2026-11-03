from app.services.registry import AgentRegistry


def test_ict_manifest_is_discoverable_but_not_dispatchable():
    registry = AgentRegistry()
    ict = registry.get("ict_mentor")
    assert ict is not None
    assert ict["status"] == "disabled"
    assert ict["mode"] == "advisory"
    assert registry.resolve_capability("ict.chart_analysis") == []


def test_unknown_capability_has_no_route():
    registry = AgentRegistry()
    assert registry.resolve_capability("ict.autonomous_execution") == []
