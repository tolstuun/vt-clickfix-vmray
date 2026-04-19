import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class VMRaySubmission(Base):
    __tablename__ = "vmray_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id"), nullable=False, unique=True, index=True
    )
    submission_id: Mapped[str | None] = mapped_column(String, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    submission_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
