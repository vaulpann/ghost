import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.analysis import AnalysisStatus, RiskLevel


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    status: AnalysisStatus
    triage_result: dict | None
    triage_flagged: bool | None
    triage_model: str | None
    triage_tokens_used: int | None
    triage_completed_at: datetime | None
    deep_analysis_result: dict | None
    deep_analysis_model: str | None
    deep_analysis_tokens_used: int | None
    deep_analysis_completed_at: datetime | None
    synthesis_result: dict | None
    risk_score: float | None
    risk_level: RiskLevel | None
    summary: str | None
    error_message: str | None
    total_cost_usd: float | None
    started_at: datetime | None
    completed_at: datetime | None
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
    type: str  # "analysis" or "finding"
    package_name: str
    package_registry: str
    version_string: str
    risk_level: RiskLevel | None
    risk_score: float | None
    summary: str | None
    finding_count: int
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
