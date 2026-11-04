import json

from app.services.knowledge_store import KnowledgeStoreAdapter
from app.storage import InMemoryStore, SQLAlchemyStore


def test_knowledge_adapter_preserves_provenance_and_retrieves(tmp_path):
    storage = SQLAlchemyStore(f"sqlite:///{tmp_path / 'knowledge.db'}")
    knowledge = KnowledgeStoreAdapter(storage)
    knowledge.save_knowledge_source(
        {
            "id": "ict-official-1",
            "title": "ICT Official Lesson",
            "url": "https://www.youtube.com/watch?v=example",
            "source_type": "video",
            "usage_basis": "public",
            "retrieved_at": "2026-11-04T10:00:00+00:00",
        },
        [{
            "ordinal": 0,
            "text": "A liquidity sweep can occur around a prior session high.",
            "timestamp_start": "00:10:00",
            "timestamp_end": "00:11:00",
        }],
    )
    results = knowledge.search_knowledge("liquidity sweep session high")
    assert len(results) == 1
    assert results[0]["source_id"] == "ict-official-1"
    assert results[0]["segment_id"] == "ict-official-1:0"
    assert results[0]["url"].startswith("https://")
    assert results[0]["timestamp_start"] == "00:10:00"
    storage.close()


def test_knowledge_adapter_rejects_non_https_and_duplicate_source():
    knowledge = KnowledgeStoreAdapter(InMemoryStore())
    source = {
        "id": "source-1", "title": "User note", "url": "http://invalid.example",
        "source_type": "user_note", "usage_basis": "user_provided",
        "retrieved_at": "2026-11-04T10:00:00+00:00",
    }
    try:
        knowledge.save_knowledge_source(source, [{"ordinal": 0, "text": "liquidity"}])
        assert False, "non-HTTPS source should be rejected"
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    source["url"] = "https://valid.example/note"
    knowledge.save_knowledge_source(source, [{"ordinal": 0, "text": "liquidity"}])
    try:
        knowledge.save_knowledge_source(source, [{"ordinal": 0, "text": "duplicate"}])
        assert False, "duplicate source ID should be rejected"
    except ValueError as exc:
        assert "immutable" in str(exc)


def test_knowledge_search_supports_persian_text():
    knowledge = KnowledgeStoreAdapter(InMemoryStore())
    knowledge.save_knowledge_source(
        {
            "id": "persian-ict-1", "title": "یادداشت نقدینگی",
            "url": "https://example.org/persian", "source_type": "user_note",
            "usage_basis": "user_provided", "retrieved_at": "2026-11-04T10:00:00+00:00",
        },
        [{"ordinal": 0, "text": "جمع‌آوری نقدینگی در سقف سشن معاملاتی"}],
    )
    results = knowledge.search_knowledge("نقدینگی سقف سشن")
    assert len(results) == 1
    assert results[0]["source_id"] == "persian-ict-1"


def test_ict_specialist_is_routed_through_core_orchestrator():
    from app.services.orchestrator import Orchestrator
    from app.services.registry import AgentRegistry

    class Router:
        def generate(self, system_prompt, user_prompt):
            return json.dumps({
                "agent_id": "ict_mentor", "mode": "advisory",
                "answer": "This is an advisory explanation.", "source_claims": [],
                "user_rules_used": [], "agent_inferences": [], "proposed_actions": [],
                "risk_decision": "not_assessed_by_specialist", "execution_result": None,
                "uncertainties": ["No source segment was retrieved for this request."],
            })

    storage = InMemoryStore()
    orchestrator = Orchestrator(AgentRegistry(), object(), storage, Router())
    task = orchestrator.submit(
        "Explain liquidity sweeps in ICT terms", task_type="ict.education",
        context={"instrument": "XAUUSD"}, principal_id="test-user",
    )
    assert task["status"] == "completed"
    assert task["assigned_agent"] == "ict_mentor"
    assert task["principal_id"] == "test-user"
    events = [event["event"] for event in storage.audit]
    assert "specialist_invocation_started" in events
    assert "specialist_invocation_completed" in events
