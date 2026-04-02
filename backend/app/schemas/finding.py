import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.finding import Severity


class FindingResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    category: str
    severity: Severity
    title: str
    description: str
    evidence: dict | None
    confidence: float
    mitre_technique: str | None
    remediation: str | None
    false_positive: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingUpdate(BaseModel):
    false_positive: bool
