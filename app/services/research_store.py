"""Immutable research and historical market-data persistence.

Tables are owned by Alembic migrations; this adapter never creates schema at runtime.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Integer, JSON, MetaData, String, Table, select, insert,
)
from sqlalchemy.exc import IntegrityError


metadata = MetaData()
strategy_versions = Table(
    "strategy_versions", metadata,
    Column("id", String(128), primary_key=True),
    Column("strategy_id", String(64), nullable=False),
    Column("version", String(32), nullable=False),
    Column("data", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
research_records = Table(
    "research_records", metadata,
    Column("id", String(128), primary_key=True),
    Column("record_type", String(32), nullable=False),
    Column("data", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
market_datasets = Table(
    "market_datasets", metadata,
    Column("id", String(128), primary_key=True),
    Column("instrument", String(64), nullable=False),
    Column("timeframe", String(16), nullable=False),
    Column("content_sha256", String(64), nullable=False),
    Column("row_count", Integer, nullable=False),
    Column("quality", JSON, nullable=False),
    Column("candles", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class ResearchStore:
    """Insert-only strategy/research records and immutable imported datasets."""

    def __init__(self, engine):
        self.engine = engine

    def create_strategy_version(self, strategy_id: str, version: str, data: dict):
        key = f"{strategy_id}:{version}"
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(strategy_versions).values(
                    id=key, strategy_id=strategy_id, version=version,
                    data=dict(data), created_at=datetime.now(timezone.utc),
                ))
        except IntegrityError as exc:
            raise ValueError("Strategy version already exists and is immutable") from exc
        return key

    def get_strategy_version(self, strategy_id: str, version: str):
        with self.engine.connect() as connection:
            row = connection.execute(
                select(strategy_versions.c.data).where(
                    strategy_versions.c.id == f"{strategy_id}:{version}"
                )
            ).first()
        return dict(row[0]) if row else None

    def save_research_record(self, record_type: str, record_id: str, data: dict):
        if record_type not in {"experiment", "strategy_transition"}:
            raise ValueError("Unsupported research record type")
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(research_records).values(
                    id=record_id, record_type=record_type, data=dict(data),
                    created_at=datetime.now(timezone.utc),
                ))
        except IntegrityError as exc:
            raise ValueError("Research records are immutable; create a new record") from exc

    def get_research_record(self, record_id: str):
        with self.engine.connect() as connection:
            row = connection.execute(
                select(research_records.c.record_type, research_records.c.data)
                .where(research_records.c.id == record_id)
            ).first()
        return {"record_type": row[0], **dict(row[1])} if row else None

    def list_strategy_transitions(self, strategy_id: str):
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(research_records.c.data)
                .where(research_records.c.record_type == "strategy_transition")
                .order_by(research_records.c.created_at.asc(), research_records.c.id.asc())
            ).all()
        return [
            dict(row[0]) for row in rows
            if row[0].get("strategy_id") == strategy_id
        ]

    def save_market_dataset(self, dataset: dict):
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(market_datasets).values(
                    id=dataset["id"], instrument=dataset["instrument"],
                    timeframe=dataset["timeframe"], content_sha256=dataset["content_sha256"],
                    row_count=dataset["row_count"], quality=dict(dataset["quality"]),
                    candles=list(dataset["candles"]), created_at=dataset["created_at"],
                ))
        except IntegrityError as exc:
            raise ValueError("Market dataset IDs are immutable") from exc

    def get_market_dataset(self, dataset_id: str):
        with self.engine.connect() as connection:
            row = connection.execute(
                select(market_datasets).where(market_datasets.c.id == dataset_id)
            ).mappings().first()
        if row is None:
            return None
        result = dict(row)
        result["quality"] = dict(result["quality"])
        result["candles"] = list(result["candles"])
        result["created_at"] = result["created_at"].isoformat()
        return result
