import json
from typing import Any, Optional

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
