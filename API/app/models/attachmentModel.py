from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.database import Base


class AssessmentAttachment(Base):
    __tablename__ = "assessment_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)

    upload_id: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[Optional[str]] = mapped_column(String(128))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1024))
    upload_status: Mapped[str] = mapped_column(String(32), default="completed")
    ocr_status: Mapped[str] = mapped_column(String(32), default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    assessment = relationship("Assessment")

    def __repr__(self) -> str:
        return f"<Attachment id={self.id} upload_id={self.upload_id} name={self.filename}>"

