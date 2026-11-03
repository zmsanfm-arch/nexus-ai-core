from pydantic import BaseModel, Field
from typing import Literal, Optional

class TaskCreate(BaseModel):
    objective: str = Field(min_length=5, max_length=4000)

class TaskView(BaseModel):
    id: str
    objective: str
    status: str
    assigned_agent: str
    risk_level: str
    result: Optional[str] = None

class ApprovalDecision(BaseModel):
    approved: bool
    reviewer: str = Field(min_length=2, max_length=120)
