from __future__ import annotations
from typing import List, Optional
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class CoverageItem(Base):
    __tablename__ = "coverage_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    base_score: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    policies: Mapped[List["PolicyCoverage"]] = relationship(
        back_populates="coverage_item"
    )
