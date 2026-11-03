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


class StrategyVersionCreate(StrictRequest):
    data: dict = Field(min_length=1)


class ExperimentCreate(StrictRequest):
    data: dict = Field(min_length=1)


class KnowledgeChunkCreate(StrictRequest):
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=12000)
    timestamp_start: str | None = None
    timestamp_end: str | None = None


class KnowledgeSourceCreate(StrictRequest):
    id: str = Field(min_length=3, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(min_length=8, max_length=2048)
    source_type: str = Field(default="web", pattern="^(web|video_transcript|document|user_upload)$")
    usage_basis: str = Field(pattern="^(official_public_excerpt|user_provided|licensed)$")
    retrieved_at: str
    metadata: dict = Field(default_factory=dict)
    chunks: list[KnowledgeChunkCreate] = Field(min_length=1)


class ICTMentorInvocationCreate(StrictRequest):
    task_type: str = Field(pattern=r"^ict\.(education|source_lookup|chart_analysis|strategy_formalization|trade_review)$")
    request: str = Field(min_length=1, max_length=8000)
    context: dict = Field(default_factory=dict)
    chart: dict | None = None
    trade: dict | None = None
    user_rules: list[dict] = Field(default_factory=list)
