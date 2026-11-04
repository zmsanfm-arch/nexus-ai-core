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


def test_ict_rejects_fabricated_source_claim_even_with_valid_source_metadata():
    import pytest
    from app.agents.ict_mentor import ICTMentorHandler
    from app.services.specialist_contract import SpecialistInput

    class Knowledge:
        def search_knowledge(self, query, limit=8):
            return [{
                "source_id": "source-1", "title": "Lesson",
                "url": "https://example.org/lesson",
                "retrieved_at": "2026-11-04T10:00:00+00:00",
                "segment_id": "source-1:0", "published_at": None,
                "timestamp_start": None, "timestamp_end": None,
                "text": "Liquidity may rest above a prior high.",
            }]

    class Router:
        def generate(self, system_prompt, user_prompt):
            return json.dumps({
                "agent_id": "ict_mentor", "mode": "advisory",
                "answer": "Unsupported claim.", "source_claims": [{
                    "claim": "The market always reverses at the prior high.",
                    "source_id": "source-1", "title": "Lesson",
                    "url": "https://example.org/lesson",
                    "retrieved_at": "2026-11-04T10:00:00+00:00",
                    "segment_id": "source-1:0", "published_at": None,
                    "timestamp_start": None, "timestamp_end": None,
                }],
                "user_rules_used": [], "agent_inferences": [],
                "proposed_actions": [], "risk_decision": "not_assessed_by_specialist",
                "execution_result": None, "uncertainties": [],
            })

    request = SpecialistInput(
        task_id="task-1", task_type="ict.source_lookup",
        request="prior high liquidity",
    )
    handler = ICTMentorHandler(Router(), Knowledge(), system_prompt="Advisory only")
    with pytest.raises(ValueError, match="exact excerpt"):
        handler.run(request)


def test_indexed_knowledge_search_normalizes_persian_and_arabic_variants(tmp_path):
    storage = SQLAlchemyStore(f"sqlite:///{tmp_path / 'indexed-persian.db'}")
    knowledge = KnowledgeStoreAdapter(storage)
    knowledge.save_knowledge_source(
        {
            "id": "persian-index-1", "title": "Persian normalization",
            "url": "https://example.org/persian-index", "source_type": "user_note",
            "usage_basis": "user_provided", "retrieved_at": "2026-11-04T10:00:00+00:00",
        },
        [{"ordinal": 0, "text": "جمع‌آوری نقدینگی در سقف سشن كليدی"}],
    )
    # Query uses Arabic Yeh/Kaf, diacritics and no ZWNJ; stored text uses Persian forms.
    results = knowledge.search_knowledge("نقدينگي سقف سشن کلیدی")
    assert len(results) == 1
    assert results[0]["source_id"] == "persian-index-1"
    storage.close()


def test_indexed_knowledge_search_backfills_existing_chunks(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'knowledge-backfill.db'}"
    storage = SQLAlchemyStore(database_url)
    knowledge = KnowledgeStoreAdapter(storage)
    knowledge.save_knowledge_source(
        {
            "id": "legacy-source", "title": "Legacy",
            "url": "https://example.org/legacy", "source_type": "document",
            "usage_basis": "user_provided", "retrieved_at": "2026-11-04T10:00:00+00:00",
        },
        [{"ordinal": 0, "text": "Legacy liquidity sweep evidence"}],
    )
    storage.close()

    # Rebuild a fresh database at migration 0001, insert legacy rows, then upgrade.
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from pathlib import Path
    import datetime

    engine = create_engine(database_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001_initial")
        connection.execute(text(
            "INSERT INTO knowledge_sources "
            "(id, title, url, source_type, usage_basis, retrieved_at) "
            "VALUES ('pre-index', 'Pre-index', 'https://example.org/pre', "
            "'document', 'user_provided', :retrieved)"
        ), {"retrieved": datetime.datetime(2026, 11, 4, 10, 0, tzinfo=datetime.timezone.utc)})
        connection.execute(text(
            "INSERT INTO knowledge_chunks (id, source_id, ordinal, text) "
            "VALUES ('pre-index:0', 'pre-index', 0, 'Historical liquidity sweep')"
        ))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    storage = SQLAlchemyStore(database_url)
    results = KnowledgeStoreAdapter(storage).search_knowledge("liquidity historical")
    assert len(results) == 1
    assert results[0]["source_id"] == "pre-index"
    storage.close()
