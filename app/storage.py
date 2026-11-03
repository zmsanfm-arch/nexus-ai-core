import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from sqlalchemy import DateTime, Integer, String, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ApprovalRecord(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class AuditRecord(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyVersionRecord(Base):
    __tablename__ = "strategy_versions"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchRecord(Base):
    __tablename__ = "research_records"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TradingRecord(Base):
    __tablename__ = "trading_records"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeSourceRecord(Base):
    __tablename__ = "knowledge_sources"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    usage_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class KnowledgeChunkRecord(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String(12000), nullable=False)
    timestamp_start: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp_end: Mapped[str | None] = mapped_column(String(64), nullable=True)


class MarketDatasetRecord(Base):
    __tablename__ = "market_datasets"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    instrument: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quality: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    candles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SQLAlchemyStore:
    """Durable SQL store; SQLite by default, PostgreSQL via DATABASE_URL."""
    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv("DATABASE_URL", "sqlite:///./data/nexus.db")
        if url.startswith("sqlite:///"):
            db_path = url.removeprefix("sqlite:///")
            if db_path and db_path != ":memory:" and not db_path.startswith("/"):
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        options = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            options["connect_args"] = {"check_same_thread": False}
        self.engine = create_engine(url, **options)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._lock = RLock()
        # SQLite is a developer/test convenience. PostgreSQL schema changes are migration-owned.
        if os.getenv("NEXUS_SKIP_SCHEMA_CREATE", "").lower() != "true" and (
            url.startswith("sqlite") or os.getenv("NEXUS_AUTO_CREATE_SCHEMA", "").lower() == "true"
        ):
            Base.metadata.create_all(self.engine)

    def save_task(self, task: dict):
        with self._lock, self.sessions.begin() as session:
            record = session.get(TaskRecord, task["id"])
            if record is None:
                record = TaskRecord(id=task["id"], data=dict(task))
                session.add(record)
            else:
                record.data = dict(task)

    def get_task(self, task_id: str):
        with self.sessions() as session:
            record = session.get(TaskRecord, task_id)
            return dict(record.data) if record else None

    def save_approval(self, approval: dict):
        with self._lock, self.sessions.begin() as session:
            record = session.get(ApprovalRecord, approval["id"])
            if record is None:
                session.add(ApprovalRecord(id=approval["id"], data=dict(approval)))
            else:
                record.data = dict(approval)

    def get_approval(self, approval_id: str):
        with self.sessions() as session:
            record = session.get(ApprovalRecord, approval_id)
            return dict(record.data) if record else None

    def append_audit(self, event: dict):
        with self._lock, self.sessions.begin() as session:
            session.add(AuditRecord(
                data=dict(event),
                recorded_at=datetime.now(timezone.utc),
            ))

    def list_audit(self, limit: int = 100):
        with self.sessions() as session:
            records = session.scalars(
                select(AuditRecord).order_by(AuditRecord.id.desc()).limit(limit)
            ).all()
            return [
                {**record.data, "recorded_at": record.recorded_at.isoformat()}
                for record in reversed(records)
            ]

    def create_strategy_version(self, strategy_id: str, version: str, data: dict):
        """Insert-only strategy version storage; existing versions are immutable."""
        key = f"{strategy_id}:{version}"
        with self._lock, self.sessions.begin() as session:
            if session.get(StrategyVersionRecord, key) is not None:
                raise ValueError("Strategy version already exists and is immutable")
            session.add(StrategyVersionRecord(
                id=key, strategy_id=strategy_id, version=version,
                data=dict(data), created_at=datetime.now(timezone.utc),
            ))
        return key

    def get_strategy_version(self, strategy_id: str, version: str):
        with self.sessions() as session:
            record = session.get(StrategyVersionRecord, f"{strategy_id}:{version}")
            return dict(record.data) if record else None

    def save_research_record(self, record_type: str, record_id: str, data: dict):
        if record_type not in {"experiment", "backtest_run", "backtest_trade", "evaluator_result", "strategy_transition"}:
            raise ValueError("Unsupported research record type")
        with self._lock, self.sessions.begin() as session:
            record = session.get(ResearchRecord, record_id)
            if record is None:
                session.add(ResearchRecord(
                    id=record_id, record_type=record_type, data=dict(data),
                    created_at=datetime.now(timezone.utc),
                ))
            else:
                if record.record_type != record_type:
                    raise ValueError("Research record type cannot change")
                if record_type == "experiment":
                    raise ValueError("Experiment plans are immutable; create a new experiment version")
                record.data = dict(data)

    def list_strategy_transitions(self, strategy_id: str):
        with self.sessions() as session:
            records = session.scalars(
                select(ResearchRecord).where(ResearchRecord.record_type == "strategy_transition")
                .order_by(ResearchRecord.created_at.asc())
            ).all()
            return [dict(record.data) for record in records if record.data.get("strategy_id") == strategy_id]

    def get_research_record(self, record_id: str):
        with self.sessions() as session:
            record = session.get(ResearchRecord, record_id)
            return {"record_type": record.record_type, **dict(record.data)} if record else None

    def save_trading_record(self, record_type: str, record_id: str, environment: str, data: dict):
        if record_type not in {"risk_event", "demo_account", "order", "position"}:
            raise ValueError("Unsupported trading record type")
        if environment not in {"research", "demo", "live"}:
            raise ValueError("Invalid environment")
        if environment == "live":
            raise ValueError("Live trading persistence is disabled")
        with self._lock, self.sessions.begin() as session:
            record = session.get(TradingRecord, record_id)
            if record is None:
                session.add(TradingRecord(
                    id=record_id, record_type=record_type, environment=environment,
                    data=dict(data), created_at=datetime.now(timezone.utc),
                ))
            else:
                if record.record_type != record_type or record.environment != environment:
                    raise ValueError("Trading record identity and environment are immutable")
                record.data = dict(data)

    def save_market_dataset(self, dataset: dict):
        with self._lock, self.sessions.begin() as session:
            if session.get(MarketDatasetRecord, dataset["id"]) is not None:
                raise ValueError("Market dataset IDs are immutable")
            session.add(MarketDatasetRecord(
                id=dataset["id"], instrument=dataset["instrument"],
                timeframe=dataset["timeframe"], content_sha256=dataset["content_sha256"],
                row_count=dataset["row_count"], quality=dict(dataset["quality"]),
                candles=list(dataset["candles"]), created_at=dataset["created_at"],
            ))

    def get_market_dataset(self, dataset_id: str):
        with self.sessions() as session:
            record = session.get(MarketDatasetRecord, dataset_id)
            if record is None:
                return None
            return {
                "id": record.id, "instrument": record.instrument,
                "timeframe": record.timeframe, "content_sha256": record.content_sha256,
                "row_count": record.row_count, "quality": dict(record.quality),
                "candles": list(record.candles), "created_at": record.created_at.isoformat(),
            }

    def save_knowledge_source(self, source: dict, chunks: list[dict]):
        """Persist provenance and bounded text segments for authorized source material."""
        allowed_basis = {"official_public_excerpt", "user_provided", "licensed"}
        if source.get("usage_basis") not in allowed_basis:
            raise ValueError("Source usage basis must be explicit and permitted")
        if not source.get("title") or not source.get("url") or not chunks:
            raise ValueError("Source title, URL and at least one chunk are required")
        with self._lock, self.sessions.begin() as session:
            if session.get(KnowledgeSourceRecord, source["id"]) is not None:
                raise ValueError("Knowledge source IDs are immutable; create a new source revision")
            session.add(KnowledgeSourceRecord(
                id=source["id"], title=source["title"], url=source["url"],
                source_type=source.get("source_type", "web"),
                usage_basis=source["usage_basis"],
                retrieved_at=source["retrieved_at"],
                metadata_json=dict(source.get("metadata", {})),
            ))
            for chunk in chunks:
                chunk_id = f'{source["id"]}:{chunk["ordinal"]}'
                session.add(KnowledgeChunkRecord(
                    id=chunk_id, source_id=source["id"], ordinal=chunk["ordinal"],
                    text=chunk["text"], timestamp_start=chunk.get("timestamp_start"),
                    timestamp_end=chunk.get("timestamp_end"),
                ))

    def search_knowledge(self, query: str, limit: int = 10):
        terms = [term.strip().lower() for term in query.split() if term.strip()]
        if not terms:
            return []
        limit = max(1, min(limit, 50))
        with self.sessions() as session:
            rows = session.query(KnowledgeChunkRecord, KnowledgeSourceRecord).join(
                KnowledgeSourceRecord, KnowledgeChunkRecord.source_id == KnowledgeSourceRecord.id
            ).all()
            ranked = []
            for chunk, source in rows:
                haystack = chunk.text.lower()
                score = sum(haystack.count(term) for term in terms)
                if score:
                    ranked.append((score, chunk, source))
            ranked.sort(key=lambda item: (-item[0], item[1].source_id, item[1].ordinal))
            return [{
                "score": score,
                "source_id": chunk.source_id,
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type,
                "usage_basis": source.usage_basis,
                "retrieved_at": source.retrieved_at.isoformat(),
                "segment_id": chunk.id,
                "timestamp_start": chunk.timestamp_start,
                "timestamp_end": chunk.timestamp_end,
                "text": chunk.text,
            } for score, chunk, source in ranked[:limit]]

    def close(self):
        self.engine.dispose()


class InMemoryStore:
    """Test-only ephemeral store; the application uses SQLAlchemyStore."""
    def __init__(self):
        self.tasks = {}
        self.approvals = {}
        self.audit = []
        self._lock = RLock()

    def save_task(self, task):
        with self._lock:
            self.tasks[task["id"]] = dict(task)

    def get_task(self, task_id):
        with self._lock:
            item = self.tasks.get(task_id)
            return dict(item) if item else None

    def save_approval(self, approval):
        with self._lock:
            self.approvals[approval["id"]] = dict(approval)

    def get_approval(self, approval_id):
        with self._lock:
            item = self.approvals.get(approval_id)
            return dict(item) if item else None

    def append_audit(self, event):
        with self._lock:
            self.audit.append({
                **event,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })


# Application default: durable SQL storage. InMemoryStore remains test-only.
store = SQLAlchemyStore()
