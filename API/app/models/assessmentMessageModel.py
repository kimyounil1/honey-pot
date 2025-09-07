from __future__ import annotations
from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class AssessmentMessage(Base):
    __tablename__ = "assessment_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessments.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(Enum('user', 'assistant', name='assessment_role_enum'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    state: Mapped[str] = mapped_column(
        Enum(
            'commencing', 'classifying', 'analyzing', 'searching', 'building', 'done', 'failed', 'complete',
            name='assessment_state_enum'
        ),
        nullable=False,
        default='done'
    )

