import json

import pytest

from app.agents.web_studio import WEB_STUDIO_ROLE_PROMPTS, WebStudioSpecialistHandler
from app.services.specialist_contract import SpecialistInput


class FakeRouter:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return json.dumps(self.payload)


def result(agent_id):
    return {
        "agent_id": agent_id,
        "mode": "advisory",
        "answer": "A bounded recommendation.",
        "source_claims": [],
        "user_rules_used": [],
        "agent_inferences": [],
        "proposed_actions": [],
        "risk_decision": "not_assessed_by_specialist",
        "execution_result": None,
        "uncertainties": [],
    }


def request():
    return SpecialistInput(
        task_id="web-task-1",
        task_type="web.frontend.build",
        request="Create a responsive landing page plan.",
        context={"dependency_outputs": {"ui_designer": {"answer": "Responsive grid"}}},
    )


def test_every_web_studio_role_has_a_distinct_role_mandate():
    assert len(WEB_STUDIO_ROLE_PROMPTS) == 21
    assert all(prompt.strip() for prompt in WEB_STUDIO_ROLE_PROMPTS.values())
    assert len(set(WEB_STUDIO_ROLE_PROMPTS.values())) == 21


def test_web_studio_handler_returns_validated_advisory_result():
    router = FakeRouter(result("web_frontend_engineer"))
    handler = WebStudioSpecialistHandler("web_frontend_engineer", router)

    output = handler.run(request())

    assert output.agent_id == "web_frontend_engineer"
    assert output.execution_result is None
    assert "frontend implementation plan" in router.calls[0][0]
    assert "dependency_outputs" in router.calls[0][1]


def test_web_studio_handler_rejects_cross_role_identity():
    router = FakeRouter(result("web_backend_engineer"))
    handler = WebStudioSpecialistHandler("web_frontend_engineer", router)

    with pytest.raises(ValueError, match="fixed identity"):
        handler.run(request())


def test_web_studio_handler_rejects_execution_result():
    payload = result("web_frontend_engineer")
    payload["execution_result"] = {"deployed": True}
    router = FakeRouter(payload)
    handler = WebStudioSpecialistHandler("web_frontend_engineer", router)

    with pytest.raises(ValueError, match="invalid advisory contract"):
        handler.run(request())


def test_unknown_web_studio_role_cannot_be_instantiated():
    with pytest.raises(ValueError, match="Unknown"):
        WebStudioSpecialistHandler("web_unknown_agent", FakeRouter({}))
