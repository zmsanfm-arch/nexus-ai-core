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
        if record_type not in {"experiment", "backtest_run", "backtest_trade", "evaluator_result"}:
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
