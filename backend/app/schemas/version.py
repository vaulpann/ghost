import uuid
from datetime import datetime

from pydantic import BaseModel


class VersionResponse(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    version_string: str
    previous_version_string: str | None
    published_at: datetime | None
    tarball_url: str | None
    sha256_digest: str | None
    diff_size_bytes: int | None
    diff_file_count: int | None
    detection_method: str
    created_at: datetime
    has_analysis: bool = False
    risk_level: str | None = None
    risk_score: float | None = None

    model_config = {"from_attributes": True}


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
    total: int
