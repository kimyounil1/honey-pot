from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, SmallInteger, String, Boolean, Numeric, CHAR, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base

class PolicyPremium(Base):
    __tablename__ = "policy_premium"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("insurance_policy.id", ondelete="CASCADE"), nullable=False)
    age_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    age_max: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[str] = mapped_column(CHAR(1), nullable=False)   # 'M','F','A'
    smoker: Mapped[Optional[bool]] = mapped_column(Boolean)
    tier: Mapped[Optional[str]] = mapped_column(String(20))        # 'basic','standard','plus' 등
    monthly_premium: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), default="KRW")
    meta: Mapped[Optional[dict]] = mapped_column(JSONB)

    policy: Mapped["InsurancePolicy"] = relationship(back_populates="premiums")
