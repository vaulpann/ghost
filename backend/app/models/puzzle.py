import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Puzzle(UUIDMixin, Base):
    __tablename__ = "puzzles"

    vulnerability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False
    )
    game_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    flavor_text: Mapped[str] = mapped_column(Text, nullable=False)
    level_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    par_time_secs: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    vulnerability: Mapped["Vulnerability"] = relationship()
    attempts: Mapped[list["PuzzleAttempt"]] = relationship(back_populates="puzzle", lazy="noload")


class PuzzleAttempt(UUIDMixin, Base):
    __tablename__ = "puzzle_attempts"

    puzzle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("puzzles.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    solved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_taken_secs: Mapped[float | None] = mapped_column(Float)
    moves: Mapped[int | None] = mapped_column(Integer)
    solution_path: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    puzzle: Mapped["Puzzle"] = relationship(back_populates="attempts")
