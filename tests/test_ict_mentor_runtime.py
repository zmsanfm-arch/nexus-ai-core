import json

from app.agents.ict_mentor import ICTMentorRuntime


class FakeStorage:
    def search_knowledge(self, query, limit=8):
        return [{
            "source_id": "s1", "title": "Official ICT excerpt",
            "url": "https://www.youtube.com/@InnerCircleTrader",
            "retrieved_at": "2026-11-04T10:00:00+00:00",
            "segment_id": "s1:0", "timestamp_start": "00:01:00",
            "timestamp_end": "00:02:00", "text": "Liquidity concepts",
        }]


class FakeModel:
    def __init__(self, response):
        self.response = response

    def generate(self, system_prompt, user_prompt):
        return json.dumps(self.response)


def base_output():
    return {
        "agent_id": "ict_mentor", "mode": "advisory", "answer": "Evidence-grounded summary.",
        "source_claims": [{
            "claim": "The excerpt discusses liquidity.",
            "source_id": "s1", "title": "Official ICT excerpt",
            "url": "https://www.youtube.com/@InnerCircleTrader",
            "retrieved_at": "2026-11-04T10:00:00+00:00",
            "segment_id": "s1:0", "timestamp_start": "00:01:00", "timestamp_end": "00:02:00",
        }],
        "user_rules_used": [], "agent_inferences": [], "proposed_actions": [],
        "risk_decision": "not_assessed_by_specialist", "execution_result": None, "uncertainties": [],
    }


def test_runtime_retrieves_and_validates_source_provenance():
    runtime = ICTMentorRuntime(FakeModel(base_output()), FakeStorage())
    result = runtime.invoke({
        "task_type": "ict.education", "mode": "advisory",
        "request": "Explain liquidity concepts",
    })
    assert result["source_claims"][0]["segment_id"] == "s1:0"
    assert result["execution_result"] is None


def test_runtime_rejects_model_claim_for_unretrieved_source():
    output = base_output()
    output["source_claims"][0]["source_id"] = "invented"
    runtime = ICTMentorRuntime(FakeModel(output), FakeStorage())
    result = runtime.invoke({
        "task_type": "ict.education", "mode": "advisory",
        "request": "Explain liquidity concepts",
    })
    assert result["source_claims"] == []
    assert result["risk_decision"] == "blocked_insufficient_information"


def test_runtime_uses_only_confirmed_user_rules():
    output = base_output()
    output["user_rules_used"] = [{"rule_id": "made-up", "text": "Use M5 entry"}]
    runtime = ICTMentorRuntime(FakeModel(output), FakeStorage())
    result = runtime.invoke({
        "task_type": "ict.education", "mode": "advisory",
        "request": "Explain liquidity concepts",
    })
    assert result["user_rules_used"] == []
    assert "not explicitly confirmed" in result["uncertainties"][0]
