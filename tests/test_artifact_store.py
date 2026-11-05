import hashlib

import pytest

from app.services.artifact_store import (
    ArtifactError,
    ArtifactNotFound,
    ArtifactTooLarge,
    LocalArtifactStore,
)


def test_artifact_round_trip_is_atomic_and_integrity_checked(tmp_path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    content = b"mission output"
    item = store.put(
        "principal-a", content, mission_id="mission_01",
        media_type="text/plain", metadata={"kind": "report"},
    )
    metadata, restored = store.get("principal-a", item["artifact_id"])
    assert restored == content
    assert metadata["sha256"] == hashlib.sha256(content).hexdigest()
    assert metadata["mission_id"] == "mission_01"
    assert metadata["metadata"] == {"kind": "report"}


def test_artifacts_are_principal_scoped(tmp_path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    item = store.put("principal-a", b"private")
    with pytest.raises(ArtifactNotFound):
        store.get("principal-b", item["artifact_id"])
    with pytest.raises(ArtifactNotFound):
        store.delete("principal-b", item["artifact_id"])


def test_size_limit_and_invalid_ids_are_rejected(tmp_path):
    store = LocalArtifactStore(tmp_path / "artifacts", max_bytes=4)
    with pytest.raises(ArtifactTooLarge):
        store.put("principal-a", b"12345")
    with pytest.raises(ArtifactError):
        store.get("principal-a", "../../etc/passwd")


def test_tampered_artifact_fails_integrity_check(tmp_path):
    root = tmp_path / "artifacts"
    store = LocalArtifactStore(root)
    item = store.put("principal-a", b"original")
    directory = next(root.iterdir())
    (directory / f'{item["artifact_id"]}.blob').write_bytes(b"tampered")
    with pytest.raises(ArtifactError, match="integrity"):
        store.get("principal-a", item["artifact_id"])


def test_delete_removes_only_owned_artifact(tmp_path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    item = store.put("principal-a", b"temporary")
    store.delete("principal-a", item["artifact_id"])
    with pytest.raises(ArtifactNotFound):
        store.get("principal-a", item["artifact_id"])
