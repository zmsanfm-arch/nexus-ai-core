"""Durable, principal-scoped storage for mission definitions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class MissionRecord(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MissionAlreadyExists(ValueError):
    pass


class MissionRepository:
    def __init__(self, storage):
        self.storage = storage

    def create(self, mission_id: str, principal_id: str, data: dict) -> dict:
        record = MissionRecord(
            id=mission_id,
            principal_id=principal_id,
            data=dict(data),
            created_at=datetime.now(timezone.utc),
        )
        try:
            with self.storage.sessions.begin() as session:
                session.add(record)
                session.flush()
        except IntegrityError as exc:
            raise MissionAlreadyExists(mission_id) from exc
        return self.get(mission_id, principal_id)

    def get(self, mission_id: str, principal_id: str) -> dict | None:
        with self.storage.sessions() as session:
            record = session.scalar(
                select(MissionRecord).where(
                    MissionRecord.id == mission_id,
                    MissionRecord.principal_id == principal_id,
                )
            )
            if record is None:
                return None
            return {
                **dict(record.data),
                "created_at": record.created_at.isoformat(),
            }
