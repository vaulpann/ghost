import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    TRIAGE_IN_PROGRESS = "triage_in_progress"
    TRIAGE_COMPLETE = "triage_complete"
    DEEP_ANALYSIS_IN_PROGRESS = "deep_analysis_in_progress"
    DEEP_ANALYSIS_COMPLETE = "deep_analysis_complete"
    SYNTHESIS_IN_PROGRESS = "synthesis_in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class RiskLevel(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Analysis(UUIDMixin, Base):
    __tablename__ = "analyses"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Triage (Pass 1)
    triage_result: Mapped[dict | None] = mapped_column(JSON)
    triage_flagged: Mapped[bool | None] = mapped_column()
    triage_model: Mapped[str | None] = mapped_column(String(50))
    triage_tokens_used: Mapped[int | None] = mapped_column(Integer)
    triage_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Deep Analysis (Pass 2)
    deep_analysis_result: Mapped[dict | None] = mapped_column(JSON)
    deep_analysis_model: Mapped[str | None] = mapped_column(String(50))
    deep_analysis_tokens_used: Mapped[int | None] = mapped_column(Integer)
    deep_analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Synthesis (Pass 3)
    synthesis_result: Mapped[dict | None] = mapped_column(JSON)
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    summary: Mapped[str | None] = mapped_column(Text)

    # Metadata
    error_message: Mapped[str | None] = mapped_column(Text)
    total_cost_usd: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    version: Mapped["Version"] = relationship(back_populates="analysis")
    findings: Mapped[list["Finding"]] = relationship(back_populates="analysis", lazy="noload")
