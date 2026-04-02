import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Registry(str, enum.Enum):
    NPM = "npm"
    PYPI = "pypi"
    GITHUB = "github"


class Priority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Package(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "packages"
    __table_args__ = (UniqueConstraint("registry", "name", name="uq_registry_name"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registry: Mapped[str] = mapped_column(String(20), nullable=False)
    registry_url: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    latest_known_version: Mapped[str | None] = mapped_column(String(100))
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    weekly_downloads: Mapped[int | None] = mapped_column(BigInteger)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    versions: Mapped[list["Version"]] = relationship(back_populates="package", lazy="noload")
