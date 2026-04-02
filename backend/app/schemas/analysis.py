import uuid
from datetime import datetime

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    status: str
    triage_result: dict | None = None
    triage_flagged: bool | None = None
    triage_model: str | None = None
    triage_tokens_used: int | None = None
    triage_completed_at: datetime | None = None
    deep_analysis_result: dict | None = None
    deep_analysis_model: str | None = None
    deep_analysis_tokens_used: int | None = None
    deep_analysis_completed_at: datetime | None = None
    synthesis_result: dict | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    summary: str | None = None
    error_message: str | None = None
    total_cost_usd: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    # Enriched fields
    package_name: str | None = None
    package_registry: str | None = None
    version_string: str | None = None
    previous_version_string: str | None = None
    finding_count: int = 0

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int
    page: int
    per_page: int


class FeedItem(BaseModel):
    id: uuid.UUID
    type: str
    package_name: str
    package_registry: str
    version_string: str
    risk_level: str | None = None
    risk_score: float | None = None
    summary: str | None = None
    finding_count: int = 0
    created_at: datetime


class FeedResponse(BaseModel):
    items: list[FeedItem]
    total: int
    page: int
    per_page: int


class StatsResponse(BaseModel):
    total_packages: int
    total_analyses: int
    analyses_today: int
    flagged_count: int
    critical_count: int
    avg_risk_score: float | None
    total_findings: int
