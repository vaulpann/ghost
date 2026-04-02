import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ChannelType(str, enum.Enum):
    SLACK = "slack"
    WEBHOOK = "webhook"
    EMAIL = "email"


class AlertStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


class AlertConfig(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alert_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    channel_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    min_risk_level: Mapped[str] = mapped_column(String(20), default="high", nullable=False)
    registries: Mapped[list | None] = mapped_column(JSON)
    packages: Mapped[list | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    history: Mapped[list["AlertHistory"]] = relationship(back_populates="alert_config")


class AlertHistory(UUIDMixin, Base):
    __tablename__ = "alert_history"

    alert_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alert_configs.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    response_data: Mapped[dict | None] = mapped_column(JSON)

    alert_config: Mapped["AlertConfig"] = relationship(back_populates="history")
    analysis: Mapped["Analysis"] = relationship()
