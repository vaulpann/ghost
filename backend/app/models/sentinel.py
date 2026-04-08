from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class SentinelScenario(UUIDMixin, Base):
    __tablename__ = "sentinel_scenarios"

    source: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    is_malicious: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attack_name: Mapped[str | None] = mapped_column(String(200))
    attack_type: Mapped[str | None] = mapped_column(String(100))

    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registry: Mapped[str] = mapped_column(String(50), nullable=False)
    version_from: Mapped[str | None] = mapped_column(String(100))
    version_to: Mapped[str | None] = mapped_column(String(100))

    # The 6 inspection dimensions
    identity_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    timing_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    shape_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    behavior_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    flow_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    context_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    used_on_date: Mapped[date | None] = mapped_column(Date)
    postmortem: Mapped[str | None] = mapped_column(Text)
    real_cve: Mapped[str | None] = mapped_column(String(50))
    real_cvss: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    verdicts: Mapped[list["SentinelVerdict"]] = relationship(back_populates="scenario", lazy="noload")


class SentinelVerdict(UUIDMixin, Base):
    __tablename__ = "sentinel_verdicts"

    scenario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sentinel_scenarios.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    attack_type_guess: Mapped[str | None] = mapped_column(String(100))
    evidence_notes: Mapped[dict | None] = mapped_column(JSON)
    time_taken_secs: Mapped[float | None] = mapped_column(Float)
    tools_used: Mapped[list | None] = mapped_column(JSON)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    scenario: Mapped["SentinelScenario"] = relationship(back_populates="verdicts")


class SentinelPlayer(Base):
    __tablename__ = "sentinel_players"

    session_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(50), default="Dock Worker", nullable=False)
    total_inspections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_flags: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_flags: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missed_attacks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detection_rate: Mapped[float | None] = mapped_column(Float)
    false_positive_rate: Mapped[float | None] = mapped_column(Float)
    vote_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
