import json
import os
from datetime import datetime, timezone, timedelta
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





class TaskQueueRecord(Base):
    __tablename__ = "task_queue"
    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


    def enqueue_task(self, task: dict):
        now = datetime.now(timezone.utc)
        with self._lock, self.sessions.begin() as session:
            existing = session.get(TaskQueueRecord, task["id"])
            if existing is not None:
                raise ValueError("Task is already queued.")
            task_record = session.get(TaskRecord, task["id"])
            if task_record is None:
                session.add(TaskRecord(id=task["id"], data=dict(task)))
            session.add(TaskQueueRecord(
                task_id=task["id"], status="queued", attempts=0,
                available_at=now, lease_owner=None, lease_expires_at=None,
                last_error=None, updated_at=now,
            ))

    def claim_next_task(self, worker_id: str, lease_seconds: int = 60):
        if not worker_id or len(worker_id) > 128 or lease_seconds < 1:
            raise ValueError("Invalid worker identity or lease duration.")
        now = datetime.now(timezone.utc)
        with self._lock, self.sessions.begin() as session:
            query = (
                select(TaskQueueRecord)
                .where(
                    TaskQueueRecord.available_at <= now,
                    (TaskQueueRecord.status == "queued") |
                    ((TaskQueueRecord.status == "leased") &
                     (TaskQueueRecord.lease_expires_at <= now)),
                )
                .order_by(TaskQueueRecord.available_at.asc(), TaskQueueRecord.task_id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            record = session.scalar(query)
            if record is None:
                return None
            record.status = "leased"
            record.attempts += 1
            record.lease_owner = worker_id
            record.lease_expires_at = now + timedelta(seconds=lease_seconds)
            record.updated_at = now
            return {"task_id": record.task_id, "attempts": record.attempts,
                    "lease_owner": worker_id, "lease_expires_at": record.lease_expires_at.isoformat()}

    def complete_queued_task(self, task_id: str, worker_id: str):
        return self._finish_queued_task(task_id, worker_id, "completed", None)

    def fail_queued_task(self, task_id: str, worker_id: str, error: str,
                         max_attempts: int = 3, retry_delay_seconds: int = 30):
        if max_attempts < 1 or retry_delay_seconds < 0:
            raise ValueError("Invalid retry policy.")
        safe_error = str(error)[:500]
        now = datetime.now(timezone.utc)
        with self._lock, self.sessions.begin() as session:
            record = session.get(TaskQueueRecord, task_id)
            if record is None or record.status != "leased" or record.lease_owner != worker_id:
                raise ValueError("Task lease is not owned by this worker.")
            record.last_error = safe_error
            record.lease_owner = None
            record.lease_expires_at = None
            record.status = "dead" if record.attempts >= max_attempts else "queued"
            record.available_at = now + timedelta(seconds=retry_delay_seconds)
            record.updated_at = now
            return record.status

    def _finish_queued_task(self, task_id: str, worker_id: str, status: str, error):
        now = datetime.now(timezone.utc)
        with self._lock, self.sessions.begin() as session:
            record = session.get(TaskQueueRecord, task_id)
            if record is None or record.status != "leased" or record.lease_owner != worker_id:
                raise ValueError("Task lease is not owned by this worker.")
            record.status = status
            record.lease_owner = None
            record.lease_expires_at = None
            record.last_error = error
            record.updated_at = now
            return status

    def close(self):
        self.engine.dispose()


class InMemoryStore:
    """Test-only ephemeral store; the application uses SQLAlchemyStore."""
    def __init__(self):
        self.tasks = {}
        self.approvals = {}
        self.audit = []
        self.queue = {}
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


    def enqueue_task(self, task):
        now = datetime.now(timezone.utc)
        with self._lock:
            if task["id"] in self.queue:
                raise ValueError("Task is already queued.")
            self.tasks[task["id"]] = dict(task)
            self.queue[task["id"]] = {
                "task_id": task["id"], "status": "queued", "attempts": 0,
                "available_at": now, "lease_owner": None, "lease_expires_at": None,
                "last_error": None, "updated_at": now,
            }

    def claim_next_task(self, worker_id, lease_seconds=60):
        if not worker_id or len(worker_id) > 128 or lease_seconds < 1:
            raise ValueError("Invalid worker identity or lease duration.")
        now = datetime.now(timezone.utc)
        with self._lock:
            candidates = [
                item for item in self.queue.values()
                if item["available_at"] <= now and (
                    item["status"] == "queued" or (
                        item["status"] == "leased" and item["lease_expires_at"] <= now
                    )
                )
            ]
            if not candidates:
                return None
            item = min(candidates, key=lambda x: (x["available_at"], x["task_id"]))
            item["status"] = "leased"
            item["attempts"] += 1
            item["lease_owner"] = worker_id
            item["lease_expires_at"] = now + timedelta(seconds=lease_seconds)
            item["updated_at"] = now
            return {**item, "lease_expires_at": item["lease_expires_at"].isoformat()}

    def complete_queued_task(self, task_id, worker_id):
        return self._finish_queued_task(task_id, worker_id, "completed", None)

    def fail_queued_task(self, task_id, worker_id, error, max_attempts=3, retry_delay_seconds=30):
        if max_attempts < 1 or retry_delay_seconds < 0:
            raise ValueError("Invalid retry policy.")
        now = datetime.now(timezone.utc)
        with self._lock:
            item = self.queue.get(task_id)
            if item is None or item["status"] != "leased" or item["lease_owner"] != worker_id:
                raise ValueError("Task lease is not owned by this worker.")
            item["last_error"] = str(error)[:500]
            item["lease_owner"] = None
            item["lease_expires_at"] = None
            item["status"] = "dead" if item["attempts"] >= max_attempts else "queued"
            item["available_at"] = now + timedelta(seconds=retry_delay_seconds)
            item["updated_at"] = now
            return item["status"]

    def _finish_queued_task(self, task_id, worker_id, status, error):
        now = datetime.now(timezone.utc)
        with self._lock:
            item = self.queue.get(task_id)
            if item is None or item["status"] != "leased" or item["lease_owner"] != worker_id:
                raise ValueError("Task lease is not owned by this worker.")
            item["status"] = status
            item["lease_owner"] = None
            item["lease_expires_at"] = None
            item["last_error"] = error
            item["updated_at"] = now
            return status

    def append_audit(self, event):
        with self._lock:
            self.audit.append({
                **event,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })


# Application default: durable SQL storage. InMemoryStore remains test-only.
store = SQLAlchemyStore()
