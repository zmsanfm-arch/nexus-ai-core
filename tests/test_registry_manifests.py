from app.services.registry import AgentRegistry


def test_ict_manifest_is_registered_for_advisory_dispatch():
    registry = AgentRegistry()
    ict = registry.get("ict_mentor")
    assert ict is not None
    assert ict["status"] == "registered"
    assert ict["mode"] == "advisory"
    assert len(registry.resolve_capability("ict.chart_analysis")) == 1


def test_unknown_capability_has_no_route():
    registry = AgentRegistry()
    assert registry.resolve_capability("ict.autonomous_execution") == []
