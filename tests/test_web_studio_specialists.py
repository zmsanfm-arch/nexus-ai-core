import json

import pytest

from app.agents.web_studio_specialists import (
    ROLE_CAPABILITIES,
    ROLE_PROMPTS,
    WebStudioSpecialistHandler,
    build_web_studio_handlers,
)
from app.services.specialist_contract import SpecialistInput


class Model:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def valid_result(agent_id):
    return json.dumps({
        "agent_id": agent_id,
        "mode": "advisory",
        "answer": "Review plan and acceptance criteria.",
        "source_claims": [],
        "user_rules_used": [],
        "agent_inferences": [{
            "inference": "A review step is needed.",
            "basis": "The request requires quality validation.",
            "confidence": "medium",
        }],
        "proposed_actions": [{
            "action": "Prepare a test plan.",
            "rationale": "Evidence is needed before acceptance.",
            "requires_central_review": True,
        }],
        "risk_decision": "not_assessed_by_specialist",
        "execution_result": None,
        "uncertainties": ["No implementation evidence was supplied."],
    })


def test_every_web_studio_role_has_a_unique_specialist_policy():
    assert len(ROLE_PROMPTS) == 21
    assert set(ROLE_PROMPTS) == set(ROLE_CAPABILITIES)
    assert len(set(ROLE_PROMPTS.values())) == 21


@pytest.mark.parametrize("agent_id", sorted(ROLE_PROMPTS))
def test_role_handler_enforces_identity_capability_and_advisory_contract(agent_id):
    model = Model(valid_result(agent_id))
    handler = WebStudioSpecialistHandler(agent_id, model)
    request = SpecialistInput(
        task_id="mission_01",
        task_type=ROLE_CAPABILITIES[agent_id],
        request="Assess the supplied website objective.",
        context={"mission_id": "mission_01", "principal_id": "principal_1"},
    )
    result = handler.run(request)
    assert result.agent_id == agent_id
    assert result.execution_result is None
    assert result.mode == "advisory"
    assert agent_id in model.calls[0][0]


def test_role_handler_rejects_capability_confusion():
    handler = WebStudioSpecialistHandler("web_seo_specialist", Model(valid_result("web_seo_specialist")))
    request = SpecialistInput(task_id="m1", task_type="web.frontend.build", request="test")
    with pytest.raises(ValueError, match="capability"):
        handler.run(request)


def test_role_handler_rejects_model_identity_spoofing():
    model = Model(valid_result("web_backend_engineer"))
    handler = WebStudioSpecialistHandler("web_frontend_engineer", model)
    request = SpecialistInput(
        task_id="m1", task_type="web.frontend.build", request="test"
    )
    with pytest.raises(ValueError, match="identity"):
        handler.run(request)


def test_role_handler_rejects_unverified_source_claims():
    payload = json.loads(valid_result("web_brief_analyst"))
    payload["source_claims"] = [{
        "claim": "fabricated", "source_id": "fake", "title": "fake",
        "url": "https://example.invalid", "retrieved_at": "now", "segment_id": "1",
    }]
    handler = WebStudioSpecialistHandler("web_brief_analyst", Model(json.dumps(payload)))
    request = SpecialistInput(
        task_id="m1", task_type="web.brief.analyze", request="test"
    )
    with pytest.raises(ValueError, match="unverified"):
        handler.run(request)


def test_factory_does_not_fake_browser_execution_when_runner_is_missing():
    handlers = build_web_studio_handlers(Model(valid_result("web_brief_analyst")))
    assert len(handlers) == 20
    assert "web_browser_tester" not in handlers


def test_factory_wires_browser_adapter_only_with_real_dependencies():
    class Store:
        def put(self, *args, **kwargs):
            return {"artifact_id": "a" * 32}
    runner = lambda request: {"report": {}, "screenshots": []}
    handlers = build_web_studio_handlers(
        Model(valid_result("web_brief_analyst")),
        browser_runner=runner,
        artifact_store=Store(),
    )
    assert len(handlers) == 21
    assert handlers["web_browser_tester"].agent_id == "web_browser_tester"
