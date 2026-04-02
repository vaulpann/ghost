import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.alert import AlertStatus, ChannelType


class AlertConfigCreate(BaseModel):
    name: str
    channel_type: ChannelType
    channel_config: dict
    min_risk_level: str = "high"
    registries: list[str] | None = None
    packages: list[str] | None = None
    enabled: bool = True


class AlertConfigUpdate(BaseModel):
    name: str | None = None
    channel_config: dict | None = None
    min_risk_level: str | None = None
    registries: list[str] | None = None
    packages: list[str] | None = None
    enabled: bool | None = None


class AlertConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    channel_type: ChannelType
    channel_config: dict
    min_risk_level: str
    registries: list[str] | None
    packages: list[str] | None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryResponse(BaseModel):
    id: uuid.UUID
    alert_config_id: uuid.UUID
    analysis_id: uuid.UUID
    sent_at: datetime
    status: AlertStatus
    response_data: dict | None

    model_config = {"from_attributes": True}
