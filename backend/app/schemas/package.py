import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.package import Priority, Registry


class PackageCreate(BaseModel):
    name: str
    registry: Registry
    registry_url: str | None = None
    repository_url: str | None = None
    description: str | None = None
    priority: Priority = Priority.MEDIUM
    monitoring_enabled: bool = True


class PackageUpdate(BaseModel):
    priority: Priority | None = None
    monitoring_enabled: bool | None = None
    description: str | None = None
    repository_url: str | None = None


class PackageResponse(BaseModel):
    id: uuid.UUID
    name: str
    registry: Registry
    registry_url: str | None
    repository_url: str | None
    description: str | None
    latest_known_version: str | None
    monitoring_enabled: bool
    priority: Priority
    weekly_downloads: int | None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PackageSeedRequest(BaseModel):
    registry: Registry
    count: int = 100


class PackageListResponse(BaseModel):
    items: list[PackageResponse]
    total: int
    page: int
    per_page: int
