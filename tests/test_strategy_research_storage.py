from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from pydantic import ValidationError

from app.services.research_routes import DataPayload, TransitionPayload

from app.services.research_store import ResearchStore
from app.storage import SQLAlchemyStore


def test_strategy_versions_are_immutable_and_retrievable(tmp_path):
    core = SQLAlchemyStore(f"sqlite:///{tmp_path / 'research.db'}")
    research = ResearchStore(core.engine)
    payload = {"strategy_id": "gold-ict", "version": "1.0.0", "status": "draft"}
    assert research.create_strategy_version("gold-ict", "1.0.0", payload) == "gold-ict:1.0.0"
    assert research.get_strategy_version("gold-ict", "1.0.0") == payload
    with pytest.raises(ValueError, match="immutable"):
        research.create_strategy_version("gold-ict", "1.0.0", {"status": "candidate"})
    core.close()


def test_experiment_records_are_insert_only(tmp_path):
    core = SQLAlchemyStore(f"sqlite:///{tmp_path / 'experiments.db'}")
    research = ResearchStore(core.engine)
    payload = {"experiment_id": "exp-001", "strategy_id": "gold-ict"}
    research.save_research_record("experiment", "exp-001", payload)
    assert research.get_research_record("exp-001") == {"record_type": "experiment", **payload}
    with pytest.raises(ValueError, match="immutable"):
        research.save_research_record("experiment", "exp-001", payload)
    core.close()


def test_market_datasets_are_immutable_and_preserve_candles(tmp_path):
    core = SQLAlchemyStore(f"sqlite:///{tmp_path / 'market.db'}")
    research = ResearchStore(core.engine)
    dataset = {
        "id": "dataset-001", "instrument": "XAUUSD", "timeframe": "M5",
        "content_sha256": "a" * 64, "row_count": 1,
        "quality": {"row_count": 1},
        "candles": [{"timestamp": "2026-01-01T00:00:00+00:00", "open": 1, "high": 2, "low": 1, "close": 2}],
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    research.save_market_dataset(dataset)
    assert research.get_market_dataset("dataset-001")["candles"] == dataset["candles"]
    with pytest.raises(ValueError, match="immutable"):
        research.save_market_dataset(dataset)
    core.close()


def test_database_rejects_mutation_and_deletion_of_research_records(tmp_path):
    core = SQLAlchemyStore(f"sqlite:///{tmp_path / 'immutable.db'}")
    research = ResearchStore(core.engine)
    research.create_strategy_version(
        "gold-ict", "1.0.0",
        {"strategy_id": "gold-ict", "version": "1.0.0", "status": "draft"},
    )
    research.save_research_record(
        "experiment", "exp-immutable", {"experiment_id": "exp-immutable"}
    )
    research.save_market_dataset({
        "id": "dataset-immutable", "instrument": "XAUUSD", "timeframe": "M5",
        "content_sha256": "b" * 64, "row_count": 1,
        "quality": {"row_count": 1},
        "candles": [{"timestamp": "2026-01-01T00:00:00+00:00", "open": 1, "high": 2, "low": 1, "close": 2}],
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    })

    mutations = [
        "UPDATE strategy_versions SET data = '{}' WHERE id = 'gold-ict:1.0.0'",
        "DELETE FROM strategy_versions WHERE id = 'gold-ict:1.0.0'",
        "UPDATE research_records SET data = '{}' WHERE id = 'exp-immutable'",
        "DELETE FROM research_records WHERE id = 'exp-immutable'",
        "UPDATE market_datasets SET row_count = 0 WHERE id = 'dataset-immutable'",
        "DELETE FROM market_datasets WHERE id = 'dataset-immutable'",
    ]
    for statement in mutations:
        with pytest.raises(DBAPIError):
            with core.engine.begin() as connection:
                connection.execute(text(statement))
    core.close()


def test_research_and_transition_payloads_have_explicit_size_limits():
    with pytest.raises(ValidationError, match="256 KiB"):
        DataPayload(data={"large": "x" * 262145})
    with pytest.raises(ValidationError, match="16 KiB"):
        TransitionPayload(target_state="candidate", evidence={"large": "x" * 17000})
