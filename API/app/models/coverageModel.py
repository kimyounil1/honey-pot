# app/models/coverageModel.py
from __future__ import annotations

from sqlalchemy import Numeric
from . import Base, Column, Integer, String, Text, ForeignKey, relationship
from sqlalchemy import UniqueConstraint

class CoverageItem(Base):
    __tablename__ = "coverage_item"

    id = Column(Integer, primary_key=True, index=True)
    # 예: "암", "뇌혈관질환", "입원일당"
    name = Column(String(200), nullable=False, unique=True, index=True)
    # 예: "질병", "상해", "진단", "입원" (선택)
    category = Column(String(100))
    # 기본 점수(폴리시별 점수가 없을 때 사용). 0~5 등 임의 스케일
    base_score = Column(Integer, nullable=False, default=0)
    description = Column(Text)

    # 역참조: 한 CoverageItem을 포함하는 PolicyCoverage들
    policies = relationship(
        "PolicyCoverage",
        back_populates="coverage_item",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_coverage_item_name"),
    )

class PolicyCoverage(Base):
    __tablename__ = "policy_coverage"

    id = Column(Integer, primary_key=True, index=True)

    # 보험상품 PK(id)와 연결 (policyModel.InsurancePolicy.id)
    policy_id = Column(Integer, ForeignKey("insurance_policy.id", ondelete="CASCADE"), nullable=False, index=True)
    # 보장 항목과 연결
    coverage_item_id = Column(Integer, ForeignKey("coverage_item.id", ondelete="CASCADE"), nullable=False, index=True)

    # 이 폴리시에 한정된 가산/대체 점수 (없으면 CoverageItem.base_score 사용)
    policy_score = Column(Integer)  # nullable=True 기본

    # 선택: 한도/공제/비고
    limit_amount = Column(Numeric(14, 2))
    notes = Column(Text)

    # 관계
    policy = relationship("InsurancePolicy", back_populates="coverages")
    coverage_item = relationship("CoverageItem", back_populates="policies")

    __table_args__ = (
        UniqueConstraint("policy_id", "coverage_item_id", name="uq_policy_coverage_pair"),
    )
