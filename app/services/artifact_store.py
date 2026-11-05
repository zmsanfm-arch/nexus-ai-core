"""Principal-scoped, atomic local artifact storage for mission outputs.

Artifacts are immutable, content-hashed files. The store never accepts a
caller-controlled filesystem path and never executes stored content.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4


class ArtifactError(ValueError):
    """Base class for rejected artifact operations."""


class ArtifactNotFound(ArtifactError):
    """Artifact does not exist or is not owned by the requesting principal."""


class ArtifactTooLarge(ArtifactError):
    """Artifact exceeds the configured byte limit."""


class LocalArtifactStore:
    """Atomic filesystem store with principal ownership and integrity metadata.

    The root directory must be on a persistent volume for durability across
    process restarts. Backups of this directory must be included in the
    operator's encrypted backup policy.
    """

    def __init__(self, root: str | Path, *, max_bytes: int = 10_485_760):
        if not 1 <= max_bytes <= 104_857_600:
            raise ValueError("max_bytes must be between 1 and 100 MiB")
        self.root = Path(root).expanduser().resolve()
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ValueError("artifact root must not be a symlink")
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass

    @staticmethod
    def _principal_key(principal_id: str) -> str:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ArtifactError("principal_id is required")
        if len(principal_id) > 256:
            raise ArtifactError("principal_id is too long")
        return hashlib.sha256(principal_id.encode("utf-8")).hexdigest()

    @staticmethod
    def _artifact_id(value: str | None = None) -> str:
        artifact_id = value or uuid4().hex
        if not re.fullmatch(r"[a-f0-9]{32}", artifact_id):
            raise ArtifactError("invalid artifact id")
        return artifact_id

    def _directory(self, principal_id: str) -> Path:
        directory = self.root / self._principal_key(principal_id)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or directory.resolve().parent != self.root:
            raise ArtifactError("invalid artifact storage directory")
        return directory

    def put(
        self,
        principal_id: str,
        content: bytes,
        *,
        media_type: str = "application/octet-stream",
        mission_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(content, bytes):
            raise ArtifactError("content must be bytes")
        if len(content) > self.max_bytes:
            raise ArtifactTooLarge("artifact exceeds configured size limit")
        if not isinstance(media_type, str) or not 1 <= len(media_type) <= 128:
            raise ArtifactError("invalid media_type")
        if mission_id is not None and (
            not isinstance(mission_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", mission_id)
        ):
            raise ArtifactError("invalid mission_id")
        safe_metadata = metadata or {}
        if not isinstance(safe_metadata, dict):
            raise ArtifactError("metadata must be an object")
        try:
            metadata_bytes = json.dumps(
                safe_metadata, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ArtifactError("metadata must be JSON serializable") from exc
        if len(metadata_bytes) > 16_384:
            raise ArtifactError("metadata exceeds configured size limit")

        directory = self._directory(principal_id)
        artifact_id = self._artifact_id()
        digest = hashlib.sha256(content).hexdigest()
        data_path = directory / f"{artifact_id}.blob"
        record = {
            "artifact_id": artifact_id,
            "principal_key": self._principal_key(principal_id),
            "mission_id": mission_id,
            "media_type": media_type,
            "size_bytes": len(content),
            "sha256": digest,
            "metadata": safe_metadata,
        }
        meta_path = directory / f"{artifact_id}.json"
        self._atomic_write(data_path, content)
        try:
            self._atomic_write(
                meta_path,
                json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            )
        except Exception:
            data_path.unlink(missing_ok=True)
            raise
        return {key: value for key, value in record.items() if key != "principal_key"}

    @staticmethod
    def _atomic_write(destination: Path, content: bytes) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=".artifact-", dir=destination.parent)
        temp_path = Path(temp_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, destination)
            try:
                dir_fd = os.open(destination.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def get(self, principal_id: str, artifact_id: str) -> tuple[dict[str, Any], bytes]:
        directory = self._directory(principal_id)
        artifact_id = self._artifact_id(artifact_id)
        meta_path = directory / f"{artifact_id}.json"
        data_path = directory / f"{artifact_id}.blob"
        try:
            record = json.loads(meta_path.read_text(encoding="utf-8"))
            content = data_path.read_bytes()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ArtifactNotFound("artifact not found") from exc
        if record.get("principal_key") != self._principal_key(principal_id):
            raise ArtifactNotFound("artifact not found")
        if len(content) != record.get("size_bytes"):
            raise ArtifactError("artifact integrity check failed")
        if hashlib.sha256(content).hexdigest() != record.get("sha256"):
            raise ArtifactError("artifact integrity check failed")
        return (
            {key: value for key, value in record.items() if key != "principal_key"},
            content,
        )

    def delete(self, principal_id: str, artifact_id: str) -> None:
        directory = self._directory(principal_id)
        artifact_id = self._artifact_id(artifact_id)
        meta_path = directory / f"{artifact_id}.json"
        data_path = directory / f"{artifact_id}.blob"
        try:
            record = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ArtifactNotFound("artifact not found") from exc
        if record.get("principal_key") != self._principal_key(principal_id):
            raise ArtifactNotFound("artifact not found")
        data_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
