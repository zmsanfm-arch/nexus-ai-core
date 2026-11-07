"""Tenant-scoped visual reference capture and indexing primitives.

This module deliberately does not fetch Instagram URLs or use private Instagram
endpoints. Media enters through an explicit user upload/share integration.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlsplit, urlunsplit

MAX_MEDIA_BYTES = 25 * 1024 * 1024
ALLOWED_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}
URL_PATTERN = re.compile(r"^/(?:p|reel|tv)/[A-Za-z0-9_-]+/?$")


class VisualInputError(ValueError):
    """Invalid or unsupported visual reference input."""


class TenantAccessError(PermissionError):
    """Raised when a reference is accessed outside its tenant/owner scope."""


class EmbeddingProvider(Protocol):
    def embed_text(self, text: str) -> list[float]: ...
    def embed_image(self, image_bytes: bytes, mime_type: str) -> list[float]: ...


@dataclass(frozen=True)
class VisualSource:
    id: str
    tenant_id: str
    owner_id: str
    source_type: str
    canonical_url: str | None
    caption: str
    labels: tuple[str, ...]
    captured_at: float
    status: str
    asset_sha256: str | None = None
    asset_path: str | None = None
    mime_type: str | None = None


def canonical_instagram_url(raw_url: str) -> str:
    """Validate and normalize a post/reel URL; never resolve or fetch it."""
    if not isinstance(raw_url, str) or len(raw_url) > 2048:
        raise VisualInputError("URL is missing or too long")
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise VisualInputError("Only HTTPS Instagram post/reel URLs are accepted")
    if parsed.username or parsed.password or parsed.port:
        raise VisualInputError("Credentials and custom ports are not allowed in URLs")
    if not URL_PATTERN.fullmatch(parsed.path):
        raise VisualInputError("URL must identify an Instagram post, reel, or TV item")
    # Keep only Instagram's harmless share tracker; reject redirect/control parameters.
    try:
        query_items = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise VisualInputError("Malformed URL query string") from exc
    if any(key != "igsh" for key, _ in query_items) or len(query_items) > 1:
        raise VisualInputError("Unsupported Instagram URL query parameters")
    if parsed.fragment:
        raise VisualInputError("URL fragments are not accepted")
    return urlunsplit(("https", "www.instagram.com", parsed.path.rstrip("/") + "/", "", ""))


def _detect_mime(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        return "video/quicktime" if brand in {b"qt  "} else "video/mp4"
    raise VisualInputError("Unsupported or unrecognized media content")


class VisualIntelligenceStore:
    """SQLite metadata store + content-addressed local media storage.

    Instantiate with a private application data directory. Do not expose this
    directory through static file serving; media must be delivered via an
    authenticated, tenant-checked handler.
    """

    def __init__(self, data_dir: str | Path):
        self.root = Path(data_dir).expanduser().resolve()
        self.media_dir = self.root / "visual-assets"
        self.media_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db_path = self.root / "visual-intelligence.sqlite3"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS visual_sources (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    canonical_url TEXT,
                    caption TEXT NOT NULL DEFAULT '',
                    labels_json TEXT NOT NULL DEFAULT '[]',
                    captured_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    asset_sha256 TEXT,
                    asset_path TEXT,
                    mime_type TEXT,
                    UNIQUE(tenant_id, owner_id, canonical_url, asset_sha256)
                );
                CREATE INDEX IF NOT EXISTS idx_visual_scope
                    ON visual_sources(tenant_id, owner_id, captured_at DESC);
            """)

    @staticmethod
    def _required_scope(tenant_id: str, owner_id: str) -> None:
        if not tenant_id or not owner_id:
            raise TenantAccessError("Authenticated tenant and principal are required")

    def capture_url(
        self, tenant_id: str, owner_id: str, url: str, *,
        caption: str = "", labels: Iterable[str] = (),
    ) -> VisualSource:
        self._required_scope(tenant_id, owner_id)
        canonical = canonical_instagram_url(url)
        clean_labels = tuple(dict.fromkeys(
            str(label).strip()[:80] for label in labels if str(label).strip()
        ))
        if len(caption) > 20_000:
            raise VisualInputError("Caption exceeds the 20,000 character limit")
        now = time.time()
        source_id = str(uuid.uuid4())
        with self._connect() as db:
            existing = db.execute(
                """SELECT * FROM visual_sources
                   WHERE tenant_id=? AND owner_id=? AND canonical_url=? AND asset_sha256 IS NULL""",
                (tenant_id, owner_id, canonical),
            ).fetchone()
            if existing:
                return self._row(existing)
            try:
                db.execute(
                    """INSERT INTO visual_sources
                       (id,tenant_id,owner_id,source_type,canonical_url,caption,labels_json,captured_at,status)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (source_id, tenant_id, owner_id, "instagram_url", canonical,
                     caption, json.dumps(clean_labels), now, "captured"),
                )
            except sqlite3.IntegrityError:
                existing = db.execute(
                    """SELECT * FROM visual_sources
                       WHERE tenant_id=? AND owner_id=? AND canonical_url=? AND asset_sha256 IS NULL""",
                    (tenant_id, owner_id, canonical),
                ).fetchone()
                if existing is None:
                    raise
                return self._row(existing)
            row = db.execute("SELECT * FROM visual_sources WHERE id=?", (source_id,)).fetchone()
        return self._row(row)

    def capture_media(
        self, tenant_id: str, owner_id: str, data: bytes, *,
        filename: str = "", caption: str = "", labels: Iterable[str] = (),
        source_url: str | None = None,
    ) -> VisualSource:
        self._required_scope(tenant_id, owner_id)
        if not isinstance(data, bytes) or not data or len(data) > MAX_MEDIA_BYTES:
            raise VisualInputError("Media must be non-empty and no larger than 25 MiB")
        mime = _detect_mime(data)
        extension = ALLOWED_TYPES[mime]
        digest = hashlib.sha256(data).hexdigest()
        canonical = canonical_instagram_url(source_url) if source_url else None
        clean_labels = tuple(dict.fromkeys(
            str(label).strip()[:80] for label in labels if str(label).strip()
        ))
        if len(caption) > 20_000:
            raise VisualInputError("Caption exceeds the 20,000 character limit")
        # Content-addressed names prevent path traversal and duplicate storage.
        target = self.media_dir / (digest + extension)
        if not target.exists():
            temp = self.media_dir / (digest + ".tmp-" + uuid.uuid4().hex)
            try:
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, target)
            finally:
                if temp.exists():
                    temp.unlink()
        now = time.time()
        source_id = str(uuid.uuid4())
        with self._connect() as db:
            existing = db.execute(
                """SELECT * FROM visual_sources
                   WHERE tenant_id=? AND owner_id=? AND asset_sha256=?""",
                (tenant_id, owner_id, digest),
            ).fetchone()
            if existing:
                return self._row(existing)
            try:
                db.execute(
                    """INSERT INTO visual_sources
                       (id,tenant_id,owner_id,source_type,canonical_url,caption,labels_json,
                        captured_at,status,asset_sha256,asset_path,mime_type)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (source_id, tenant_id, owner_id, "media_upload", canonical, caption,
                     json.dumps(clean_labels), now, "captured", digest, str(target), mime),
                )
            except sqlite3.IntegrityError:
                existing = db.execute(
                    """SELECT * FROM visual_sources
                       WHERE tenant_id=? AND owner_id=? AND asset_sha256=?""",
                    (tenant_id, owner_id, digest),
                ).fetchone()
                if existing is None:
                    raise
                return self._row(existing)
            row = db.execute("SELECT * FROM visual_sources WHERE id=?", (source_id,)).fetchone()
        return self._row(row)

    def list_sources(self, tenant_id: str, owner_id: str, *, limit: int = 100) -> list[VisualSource]:
        self._required_scope(tenant_id, owner_id)
        if not 1 <= limit <= 500:
            raise VisualInputError("limit must be between 1 and 500")
        with self._connect() as db:
            rows = db.execute(
                """SELECT * FROM visual_sources WHERE tenant_id=? AND owner_id=?
                   ORDER BY captured_at DESC LIMIT ?""",
                (tenant_id, owner_id, limit),
            ).fetchall()
        return [self._row(row) for row in rows]

    def get_asset(self, tenant_id: str, owner_id: str, source_id: str) -> tuple[Path, str]:
        self._required_scope(tenant_id, owner_id)
        with self._connect() as db:
            row = db.execute(
                """SELECT asset_path,mime_type FROM visual_sources
                   WHERE id=? AND tenant_id=? AND owner_id=?""",
                (source_id, tenant_id, owner_id),
            ).fetchone()
        if not row or not row["asset_path"] or not row["mime_type"]:
            raise TenantAccessError("Asset not found in this tenant/principal scope")
        path = Path(row["asset_path"]).resolve()
        if path.parent != self.media_dir or not path.is_file():
            raise VisualInputError("Stored asset is unavailable")
        return path, row["mime_type"]

    def search(self, tenant_id: str, owner_id: str, query: str, *, limit: int = 20) -> list[VisualSource]:
        """Safe lexical fallback; vector retrieval can be added behind the same scope."""
        self._required_scope(tenant_id, owner_id)
        terms = [t.lower() for t in re.findall(r"[\w-]{2,}", query)][:20]
        if not terms:
            return []
        rows = self.list_sources(tenant_id, owner_id, limit=500)
        ranked = []
        for source in rows:
            haystack = (source.caption + " " + " ".join(source.labels) + " " +
                        (source.canonical_url or "")).lower()
            score = sum(haystack.count(term) for term in terms)
            if score:
                ranked.append((score, source.captured_at, source))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in ranked[:max(1, min(limit, 100))]]

    @staticmethod
    def _row(row: sqlite3.Row) -> VisualSource:
        return VisualSource(
            id=row["id"], tenant_id=row["tenant_id"], owner_id=row["owner_id"],
            source_type=row["source_type"], canonical_url=row["canonical_url"],
            caption=row["caption"], labels=tuple(json.loads(row["labels_json"])),
            captured_at=row["captured_at"], status=row["status"],
            asset_sha256=row["asset_sha256"], asset_path=row["asset_path"],
            mime_type=row["mime_type"],
        )
