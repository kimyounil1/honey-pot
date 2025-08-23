from __future__ import annotations
from typing import List, Optional
from sqlalchemy import Integer, String, Date, Text, Boolean, SmallInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
from .enums import product_type_enum, renewal_type_enum, ProductType, RenewalType

def _User():
    from .userModel import User
    return User

def _Prediction():
    from .userModel import Prediction
    return Prediction

class InsurancePolicy(Base):
    __tablename__ = "insurance_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ✅ Postgres 예약어 테이블은 반드시 인용: "user"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('"user".user_id'), nullable=False)
    policy_id: Mapped[Optional[str]] = mapped_column(String(128))
    insurer: Mapped[Optional[str]] = mapped_column(String(255))
    product_code: Mapped[Optional[str]] = mapped_column(String(100))
    version: Mapped[Optional[str]] = mapped_column(String(100))
    effective_date: Mapped[Optional[Date]] = mapped_column(Date)
    policy_type: Mapped[Optional[str]] = mapped_column(String(100))
    coverage_summary: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[Optional[Date]] = mapped_column(Date)
    end_date: Mapped[Optional[Date]] = mapped_column(Date)
    coverage_item_names: Mapped[list] = mapped_column(JSONB, nullable=False)

    # === 확장 컬럼(추천용 메타) ===
    product_type: Mapped[Optional[ProductType]] = mapped_column(product_type_enum, nullable=True)
    renewal_type: Mapped[Optional[RenewalType]] = mapped_column(renewal_type_enum, nullable=True)
    waiting_period_days: Mapped[Optional[int]] = mapped_column(Integer)
    age_min: Mapped[Optional[int]] = mapped_column(SmallInteger)
    age_max: Mapped[Optional[int]] = mapped_column(SmallInteger)
    gender_allowed: Mapped[Optional[str]] = mapped_column(String(1))  # 'M','F','A'
    is_catalog: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attrs: Mapped[Optional[dict]] = mapped_column(JSONB)

    # 관계
    coverages: Mapped[List["PolicyCoverage"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    premiums: Mapped[List["PolicyPremium"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    non_benefit_links: Mapped[List["PolicyNonBenefitMap"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    # use lazy callables to avoid import-order issues
    predictions = relationship(_Prediction, back_populates="policy", cascade="all, delete-orphan")
    user = relationship(_User, back_populates="insurance_policies")

    def __repr__(self) -> str:
        return f"<InsurancePolicy id={self.id} insurer={self.insurer} code={self.product_code}>"
