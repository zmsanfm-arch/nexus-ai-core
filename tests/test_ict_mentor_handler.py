import json

import pytest

from app.agents.ict_mentor import ICTMentorHandler
from app.services.specialist_contract import SpecialistInput


class FakeStorage:
    def __init__(self, sources=None):
        self.sources = sources or []

    def search_knowledge(self, query, limit=8):
        assert query == "Explain a sourced ICT concept"
        assert limit == 8
        return self.sources


class FakeRouter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return json.dumps(self.result)


def valid_result(**overrides):
    result = {
        "agent_id": "ict_mentor",
        "mode": "advisory",
        "answer": "Advisory explanation only.",
        "source_claims": [],
        "user_rules_used": [],
        "agent_inferences": [],
        "proposed_actions": [],
        "risk_decision": "not_assessed_by_specialist",
        "execution_result": None,
        "uncertainties": [],
    }
    result.update(overrides)
    return result


def make_request(**overrides):
    values = {
        "task_id": "task-ict-1",
        "task_type": "ict.education",
        "request": "Explain a sourced ICT concept",
    }
    values.update(overrides)
    return SpecialistInput(**values)


def test_ict_handler_returns_only_validated_advisory_contract():
    router = FakeRouter(valid_result())
    handler = ICTMentorHandler(router, FakeStorage(), system_prompt="fixed system prompt")

    result = handler.run(make_request())

    assert result.agent_id == "ict_mentor"
    assert result.mode == "advisory"
    assert result.execution_result is None
    assert router.calls[0][0] == "fixed system prompt"


def test_ict_handler_rejects_source_claim_not_in_central_retrieval():
    router = FakeRouter(valid_result(source_claims=[{
        "claim": "A source-backed claim",
        "source_id": "invented",
        "title": "Invented",
        "url": "https://example.org/source",
        "retrieved_at": "2026-11-04T10:00:00Z",
        "segment_id": "invented:0",
    }]))
    handler = ICTMentorHandler(router, FakeStorage(), system_prompt="fixed")

    with pytest.raises(ValueError, match="not retrieved by NEXUS"):
        handler.run(make_request())


def test_ict_handler_rejects_unconfirmed_user_rule():
    router = FakeRouter(valid_result(user_rules_used=[{
        "rule_id": "R-unknown",
        "text": "A rule the user did not confirm",
    }]))
    handler = ICTMentorHandler(router, FakeStorage(), system_prompt="fixed")

    with pytest.raises(ValueError, match="not explicitly confirmed"):
        handler.run(make_request())


def test_ict_handler_ignores_client_supplied_source_metadata():
    router = FakeRouter(valid_result())
    handler = ICTMentorHandler(router, FakeStorage(), system_prompt="fixed")
    request = make_request(retrieved_sources=[{
        "source_id": "client-source",
        "title": "Untrusted client source",
        "url": "https://attacker.example",
        "retrieved_at": "2026-11-04T10:00:00Z",
        "segment_id": "client-source:0",
    }])

    result = handler.run(request)

    prompt = router.calls[0][1]
    assert "Untrusted client source" not in prompt
    assert result.execution_result is None
