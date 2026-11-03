import json
from typing import Any, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(StrictRequest):
    objective: str = Field(min_length=5, max_length=4000)
    task_type: Optional[str] = Field(default=None, min_length=1, max_length=128)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def context_must_be_bounded_json(cls, value):
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Task context must contain JSON-compatible values.") from exc
        if len(encoded.encode("utf-8")) > 16_384:
            raise ValueError("Task context exceeds the 16 KiB limit.")
        return value


class TaskView(BaseModel):
    id: str
    objective: str
    status: str
    assigned_agent: Optional[str] = None
    risk_level: str
    result: Optional[str] = None
    task_type: Optional[str] = None


class ApprovalDecision(StrictRequest):
    approved: bool


class KnowledgeChunkCreate(StrictRequest):
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=12000)
    timestamp_start: Optional[str] = Field(default=None, max_length=64)
    timestamp_end: Optional[str] = Field(default=None, max_length=64)


class KnowledgeSourceCreate(StrictRequest):
    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(min_length=1, max_length=2048)
    source_type: Literal["video", "document", "transcript", "user_note", "other"]
    usage_basis: Literal["public", "licensed", "user_provided", "permissioned"]
    retrieved_at: datetime
    chunks: list[KnowledgeChunkCreate] = Field(min_length=1, max_length=500)

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_requires_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value

    @field_validator("chunks")
    @classmethod
    def chunk_ordinals_must_be_unique(cls, value):
        ordinals = [item.ordinal for item in value]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("Chunk ordinals must be unique")
        return value
