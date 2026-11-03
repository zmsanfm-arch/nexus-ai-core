import pytest

from app.services.permissions import PermissionDenied, PermissionService


def test_empty_manifest_permissions_deny_ict_capability():
    service = PermissionService()
    agent = {"id": "ict_mentor", "mode": "advisory", "permissions": []}
    with pytest.raises(PermissionDenied, match="not been granted"):
        service.authorize(agent, "ict.education")


def test_manifest_permission_cannot_override_core_denylist():
    service = PermissionService(allowed_permissions=frozenset())
    agent = {
        "id": "ict_mentor",
        "mode": "advisory",
        "permissions": ["user_input.read"],
    }
    with pytest.raises(PermissionDenied, match="not allowed"):
        service.authorize(agent, "ict.education")


def test_unknown_capability_fails_closed():
    service = PermissionService()
    agent = {"id": "ict_mentor", "mode": "advisory", "permissions": ["*"]}
    with pytest.raises(PermissionDenied, match="No central permission policy"):
        service.authorize(agent, "ict.autonomous_execution")


def test_authorized_advisory_capability_requires_both_sides_to_allow():
    service = PermissionService()
    agent = {
        "id": "ict_mentor",
        "mode": "advisory",
        "permissions": ["chart_attachment.read"],
    }
    assert service.authorize(agent, "ict.chart_analysis") == "chart_attachment.read"


def test_non_advisory_mode_is_denied():
    service = PermissionService()
    agent = {
        "id": "ict_mentor",
        "mode": "execution",
        "permissions": ["user_input.read"],
    }
    with pytest.raises(PermissionDenied, match="Only advisory"):
        service.authorize(agent, "ict.education")



def test_forex_permission_requests_are_not_implicit_grants():
    from app.services.registry import AgentRegistry

    agent = AgentRegistry().get("ict_mentor")
    assert agent["requested_permissions"] == [
        "knowledge.retrieve",
        "user_input.read",
        "chart_attachment.read",
    ]
    assert agent["permissions"] == []
    with pytest.raises(PermissionDenied, match="not been granted"):
        PermissionService().authorize(agent, "ict.chart_analysis")
