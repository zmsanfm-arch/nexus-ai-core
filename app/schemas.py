from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreate(StrictRequest):
    objective: str = Field(min_length=5, max_length=4000)


class TaskView(BaseModel):
    id: str
    objective: str
    status: str
    assigned_agent: str
    risk_level: str
    result: Optional[str] = None


class ApprovalDecision(StrictRequest):
    approved: bool
