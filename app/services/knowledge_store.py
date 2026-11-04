"""Central, provenance-preserving knowledge storage adapter for specialists."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import (
    MetaData, Table, Column, String, Integer, DateTime, select, insert,
    func, distinct,
)

metadata = MetaData()
sources = Table(
    "knowledge_sources", metadata,
    Column("id", String(128), primary_key=True),
    Column("title", String(512), nullable=False),
    Column("url", String(2048), nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("usage_basis", String(32), nullable=False),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
)
chunks = Table(
    "knowledge_chunks", metadata,
    Column("id", String(160), primary_key=True),
    Column("source_id", String(128), nullable=False, index=True),
    Column("ordinal", Integer, nullable=False),
    Column("text", String(12000), nullable=False),
    Column("timestamp_start", String(64), nullable=True),
    Column("timestamp_end", String(64), nullable=True),
)
chunk_terms = Table(
    "knowledge_chunk_terms", metadata,
    Column("chunk_id", String(160), primary_key=True),
    Column("term", String(128), primary_key=True, index=True),
)


class KnowledgeStoreAdapter:
    """NEXUS-owned knowledge retrieval; no specialist-provided source is trusted."""

    def __init__(self, storage):
        self.storage = storage
        self.engine = getattr(storage, "engine", None)
        self._memory_sources = {}
        self._memory_chunks = []

    @staticmethod
    def _tokens(value: str) -> set[str]:
        # Canonicalize Persian/Arabic variants, compatibility forms, marks and ZWNJ.
        value = unicodedata.normalize("NFKC", value).translate(str.maketrans({
            "ي": "ی", "ى": "ی", "ك": "ک", "ـ": "",
        }))
        value = "".join(
            char for char in value
            if unicodedata.category(char) not in {"Mn", "Me", "Cf"}
        ).casefold()
        return {
            token for token in re.findall(r"[^\\W_]{2,}", value, flags=re.UNICODE)
            if len(token) <= 128
        }

    def save_knowledge_source(self, source: dict, source_chunks: list[dict]) -> None:
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Knowledge source URL must be HTTPS")
        source_id = source.get("id")
        if not source_id or len(source_id) > 128:
            raise ValueError("Invalid knowledge source ID")
        retrieved_at = source.get("retrieved_at")
        if isinstance(retrieved_at, str):
            retrieved_at = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        if (not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None
                or retrieved_at.utcoffset() is None):
            raise ValueError("retrieved_at must be timezone-aware")
        normalized = []
        seen = set()
        for item in source_chunks:
            ordinal = item.get("ordinal")
            text = item.get("text")
            if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0 or ordinal in seen:
                raise ValueError("Chunk ordinals must be unique non-negative integers")
            if not isinstance(text, str) or not text.strip() or len(text) > 12000:
                raise ValueError("Chunk text must contain 1 to 12000 characters")
            seen.add(ordinal)
            normalized.append({
                "id": f"{source_id}:{ordinal}", "source_id": source_id,
                "ordinal": ordinal, "text": text,
                "timestamp_start": item.get("timestamp_start"),
                "timestamp_end": item.get("timestamp_end"),
            })
        source_row = {
            "id": source_id, "title": source["title"], "url": source["url"],
            "source_type": source.get("source_type", "document"),
            "usage_basis": source.get("usage_basis", "user_provided"),
            "retrieved_at": retrieved_at,
        }
        if self.engine is None:
            if source_id in self._memory_sources:
                raise ValueError("Knowledge source IDs are immutable")
            self._memory_sources[source_id] = source_row
            self._memory_chunks.extend(normalized)
            return
        with self.engine.begin() as connection:
            if connection.execute(select(sources.c.id).where(sources.c.id == source_id)).first():
                raise ValueError("Knowledge source IDs are immutable")
            connection.execute(insert(sources).values(**source_row))
            if normalized:
                connection.execute(insert(chunks), normalized)
                term_rows = [
                    {"chunk_id": chunk["id"], "term": term}
                    for chunk in normalized for term in self._tokens(chunk["text"])
                ]
                if term_rows:
                    connection.execute(insert(chunk_terms), term_rows)

    def search_knowledge(self, query: str, limit: int = 8) -> list[dict]:
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            return []
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 20:
            raise ValueError("Knowledge search limit must be between 1 and 20")
        terms = self._tokens(query)
        if not terms:
            return []
        if self.engine is None:
            rows = []
            for chunk in self._memory_chunks:
                score = len(terms & self._tokens(chunk["text"]))
                if score:
                    rows.append((score, {**chunk, **self._memory_sources[chunk["source_id"]]}))
            rows.sort(key=lambda item: (
                -item[0], item[1]["source_id"], item[1]["id"]
            ))
            matches = [(score, row) for score, row in rows[:limit]]
        else:
            scores = (
                select(
                    chunk_terms.c.chunk_id.label("chunk_id"),
                    func.count(distinct(chunk_terms.c.term)).label("score"),
                )
                .where(chunk_terms.c.term.in_(sorted(terms)))
                .group_by(chunk_terms.c.chunk_id)
                .subquery()
            )
            statement = (
                select(
                    scores.c.score, chunks.c.id.label("segment_id"),
                    chunks.c.source_id, chunks.c.text, chunks.c.timestamp_start,
                    chunks.c.timestamp_end, sources.c.title, sources.c.url,
                    sources.c.source_type, sources.c.usage_basis, sources.c.retrieved_at,
                )
                .select_from(
                    scores.join(chunks, chunks.c.id == scores.c.chunk_id)
                    .join(sources, chunks.c.source_id == sources.c.id)
                )
                .order_by(scores.c.score.desc(), chunks.c.source_id, chunks.c.id)
                .limit(limit)
            )
            with self.engine.connect() as connection:
                matches = [(row.score, dict(row._mapping)) for row in connection.execute(statement)]
        results = []
        for _, row in matches:
            retrieved = row["retrieved_at"]
            if isinstance(retrieved, datetime):
                if retrieved.tzinfo is None:
                    retrieved = retrieved.replace(tzinfo=timezone.utc)
                retrieved = retrieved.isoformat()
            results.append({
                "source_id": row["source_id"], "title": row["title"],
                "url": row["url"], "retrieved_at": retrieved,
                "segment_id": row.get("segment_id") or row["id"],
                "text": row["text"], "timestamp_start": row.get("timestamp_start"),
                "timestamp_end": row.get("timestamp_end"),
                "source_type": row.get("source_type"), "usage_basis": row.get("usage_basis"),
            })
        return results
