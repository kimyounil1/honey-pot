from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class PolicyCoverage(Base):
    __tablename__ = "policy_coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("insurance_policy.id", ondelete="CASCADE"), nullable=False)
    coverage_item_id: Mapped[int] = mapped_column(ForeignKey("coverage_item.id", ondelete="CASCADE"), nullable=False)
    policy_score: Mapped[Optional[int]] = mapped_column(Integer)
    limit_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    policy: Mapped["InsurancePolicy"] = relationship(back_populates="coverages")
    coverage_item: Mapped["CoverageItem"] = relationship(back_populates="policies")
