from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(StrictRequest):
    objective: str = Field(min_length=5, max_length=4000)
    task_type: Optional[str] = Field(default=None, min_length=1, max_length=128)
    context: dict[str, Any] = Field(default_factory=dict)


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
