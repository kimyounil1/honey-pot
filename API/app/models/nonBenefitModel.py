from __future__ import annotations
from typing import List, Optional
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class NonBenefitItem(Base):
    __tablename__ = "non_benefit_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq_no: Mapped[Optional[str]] = mapped_column(String(50))
    code: Mapped[Optional[str]] = mapped_column(String(50))
    category_mid: Mapped[Optional[str]] = mapped_column(Text)
    category_small: Mapped[Optional[str]] = mapped_column(Text)
    category_detail: Mapped[Optional[str]] = mapped_column(Text)
    note: Mapped[Optional[str]] = mapped_column(Text)
    extra_1: Mapped[Optional[str]] = mapped_column(Text)
    extra_2: Mapped[Optional[str]] = mapped_column(Text)
    extra_3: Mapped[Optional[str]] = mapped_column(Text)
