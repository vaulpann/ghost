import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Version(UUIDMixin, Base):
    __tablename__ = "versions"

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    version_string: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_version_string: Mapped[str | None] = mapped_column(String(100))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tarball_url: Mapped[str | None] = mapped_column(Text)
    sha256_digest: Mapped[str | None] = mapped_column(String(64))
    diff_size_bytes: Mapped[int | None] = mapped_column(Integer)
    diff_file_count: Mapped[int | None] = mapped_column(Integer)
    diff_content: Mapped[str | None] = mapped_column(Text)
    detection_method: Mapped[str] = mapped_column(String(50), default="poll")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    package: Mapped["Package"] = relationship(back_populates="versions")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="version", uselist=False)
