"""Transactional persistence and queue operations for resumable mission runs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class MissionRunRecord(Base):
    __tablename__ = "mission_runs"
    __table_args__ = (
        UniqueConstraint("mission_id", "principal_id", "idempotency_key",
                         name="uq_mission_run_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MissionNodeRunRecord(Base):
    __tablename__ = "mission_node_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MissionQueueRecord(Base):
    __tablename__ = "mission_queue"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MissionRunRepository:
    """Mission-specific durable queue with lease-based crash recovery.

    A worker may repeat a handler after losing its lease during an external
    process crash. Completed node checkpoints are never scheduled again.
    Handlers must remain advisory/idempotent; external side effects are absent.
    """

    def __init__(self, storage):
        self.storage = storage

    def enqueue(self, mission_id: str, principal_id: str, idempotency_key: str,
                mission_data: dict[str, Any]) -> dict:
        if not idempotency_key or len(idempotency_key) > 128:
            raise ValueError("A valid idempotency key is required.")
        now = datetime.now(timezone.utc)
        run_id = str(uuid4())
        nodes = mission_data.get("nodes", [])
        try:
            with self.storage.sessions.begin() as session:
                record = MissionRunRecord(
                    id=run_id, mission_id=mission_id, principal_id=principal_id,
                    idempotency_key=idempotency_key, status="queued",
                    data=dict(mission_data), created_at=now, updated_at=now,
                )
                session.add(record)
                for node in nodes:
                    session.add(MissionNodeRunRecord(
                        run_id=run_id, node_id=node["node_id"], status="pending",
                        attempts=0, output=None, last_error=None, updated_at=now,
                    ))
                session.add(MissionQueueRecord(
                    run_id=run_id, status="queued", attempts=0, available_at=now,
                    lease_owner=None, lease_expires_at=None, last_error=None, updated_at=now,
                ))
                session.flush()
        except IntegrityError:
            with self.storage.sessions() as session:
                existing = session.scalar(select(MissionRunRecord).where(
                    MissionRunRecord.mission_id == mission_id,
                    MissionRunRecord.principal_id == principal_id,
                    MissionRunRecord.idempotency_key == idempotency_key,
                ))
                if existing is None:
                    raise
                return self._serialize(existing, session)
        with self.storage.sessions() as session:
            return self._serialize(session.get(MissionRunRecord, run_id), session)

    @staticmethod
    def _serialize(record, session) -> dict:
        nodes = session.scalars(
            select(MissionNodeRunRecord).where(
                MissionNodeRunRecord.run_id == record.id
            ).order_by(MissionNodeRunRecord.node_id)
        ).all()
        return {
            "run_id": record.id, "mission_id": record.mission_id,
            "principal_id": record.principal_id, "status": record.status,
            "idempotency_key": record.idempotency_key,
            "nodes": [{
                "node_id": node.node_id, "status": node.status,
                "attempts": node.attempts, "output": node.output,
                "last_error": node.last_error,
            } for node in nodes],
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    def get(self, run_id: str, principal_id: str) -> dict | None:
        with self.storage.sessions() as session:
            record = session.scalar(select(MissionRunRecord).where(
                MissionRunRecord.id == run_id,
                MissionRunRecord.principal_id == principal_id,
            ))
            return self._serialize(record, session) if record else None

    def get_for_worker(self, run_id: str) -> dict | None:
        """Internal worker read; API callers must use principal-scoped get()."""
        with self.storage.sessions() as session:
            record = session.get(MissionRunRecord, run_id)
            return self._serialize(record, session) if record else None

    def claim_next(self, worker_id: str, lease_seconds: int = 600) -> dict | None:
        if not worker_id or len(worker_id) > 128 or lease_seconds < 1:
            raise ValueError("Invalid worker identity or lease duration.")
        now = datetime.now(timezone.utc)
        with self.storage.sessions.begin() as session:
            record = session.scalar(
                select(MissionQueueRecord).where(
                    MissionQueueRecord.available_at <= now,
                    (MissionQueueRecord.status == "queued") |
                    ((MissionQueueRecord.status == "leased") &
                     (MissionQueueRecord.lease_expires_at <= now)),
                ).order_by(MissionQueueRecord.available_at, MissionQueueRecord.run_id)
                 .with_for_update(skip_locked=True).limit(1)
            )
            if record is None:
                return None
            record.status = "leased"
            record.attempts += 1
            record.lease_owner = worker_id
            record.lease_expires_at = now + timedelta(seconds=lease_seconds)
            record.updated_at = now
            run = session.get(MissionRunRecord, record.run_id)
            run.status = "running"
            run.updated_at = now
            return {"run_id": record.run_id, "attempts": record.attempts,
                    "lease_owner": worker_id,
                    "lease_expires_at": record.lease_expires_at.isoformat()}

    def checkpoint_node(self, run_id: str, worker_id: str, node_id: str,
                        status: str, *, output: dict | None = None,
                        error: str | None = None, increment_attempt: bool = False) -> None:
        if status not in {"running", "completed", "failed", "blocked"}:
            raise ValueError("Invalid mission node status.")
        now = datetime.now(timezone.utc)
        with self.storage.sessions.begin() as session:
            queue = session.scalar(select(MissionQueueRecord).where(
                MissionQueueRecord.run_id == run_id,
                MissionQueueRecord.status == "leased",
                MissionQueueRecord.lease_owner == worker_id,
                MissionQueueRecord.lease_expires_at > now,
            ).with_for_update())
            if queue is None:
                raise ValueError("Mission lease is not owned by this worker.")
            node = session.scalar(select(MissionNodeRunRecord).where(
                MissionNodeRunRecord.run_id == run_id,
                MissionNodeRunRecord.node_id == node_id,
            ).with_for_update())
            if node is None:
                raise KeyError(node_id)
            if node.status == "completed" and status != "completed":
                raise ValueError("A completed node checkpoint is immutable.")
            node.status = status
            if increment_attempt:
                node.attempts += 1
            if output is not None:
                node.output = dict(output)
            node.last_error = error[:500] if error else None
            node.updated_at = now

    def finish(self, run_id: str, worker_id: str, status: str,
               error: str | None = None, retry_delay_seconds: int = 30,
               max_attempts: int = 3) -> str:
        if status not in {"completed", "failed", "blocked", "review_required", "nodes_succeeded"}:
            raise ValueError("Invalid terminal mission status.")
        now = datetime.now(timezone.utc)
        with self.storage.sessions.begin() as session:
            queue = session.scalar(select(MissionQueueRecord).where(
                MissionQueueRecord.run_id == run_id,
                MissionQueueRecord.status == "leased",
                MissionQueueRecord.lease_owner == worker_id,
                MissionQueueRecord.lease_expires_at > now,
            ).with_for_update())
            if queue is None:
                raise ValueError("Mission lease is not owned by this worker.")
            run = session.get(MissionRunRecord, run_id)
            if status == "failed" and queue.attempts < max_attempts:
                queue.status = "queued"
                queue.available_at = now + timedelta(seconds=max(0, retry_delay_seconds))
                run.status = "queued"
            else:
                queue.status = "dead" if status == "failed" else "completed"
                run.status = "failed" if status == "failed" else status
            queue.last_error = error[:500] if error else None
            queue.lease_owner = None
            queue.lease_expires_at = None
            queue.updated_at = now
            run.updated_at = now
            return run.status
