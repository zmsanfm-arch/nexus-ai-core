from datetime import timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.storage import Base
from app.services.mission_repository import (
    MissionAlreadyExists,
    MissionRepository,
)


class TestStorage:
    def __init__(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)


def test_mission_repository_persists_and_scopes_by_principal():
    storage = TestStorage()
    repository = MissionRepository(storage)
    data = {"mission_id": "demo_mission", "name": "Demo", "nodes": []}

    created = repository.create("demo_mission", "principal-a", data)

    assert created["mission_id"] == "demo_mission"
    assert created["name"] == "Demo"
    assert created["created_at"]
    assert repository.get("demo_mission", "principal-a")["name"] == "Demo"
    assert repository.get("demo_mission", "principal-b") is None


def test_mission_repository_rejects_duplicate_ids():
    storage = TestStorage()
    repository = MissionRepository(storage)
    repository.create("demo_mission", "principal-a", {"name": "First"})

    try:
        repository.create("demo_mission", "principal-a", {"name": "Second"})
    except MissionAlreadyExists:
        pass
    else:
        raise AssertionError("duplicate mission IDs must be rejected")
