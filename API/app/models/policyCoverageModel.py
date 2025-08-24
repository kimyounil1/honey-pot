from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, Numeric, Text, ForeignKey, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class PolicyCoverage(Base):
    __tablename__ = "policy_coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("insurance_policy.id", ondelete="CASCADE"),
        nullable=False
    )
    coverage_item_id: Mapped[int] = mapped_column(
        ForeignKey("coverage_item.id", ondelete="CASCADE"),
        nullable=False
    )

    # 점수(예: 내부 평가 스코어)
    policy_score: Mapped[Optional[int]] = mapped_column(Integer)

    # 기존 한도 금액(기존 필드 유지)
    limit_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))

    # 메모/비고
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # === 추가된 컬럼들 ===

    # 보장 세그먼트: '입원','외래','처방','응급'
    segment: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="보장 세그먼트: '입원','외래','처방','응급'"
    )

    # 급여 유형: '급여','비급여','선택'
    benefit_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="급여 유형: '급여','비급여','선택'"
    )

    # 본인부담률(예: 0.2 = 20%)
    coinsurance_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4),
        comment="본인부담률(예: 0.2 = 20%)"
    )

    # 회당 공제 최저액(원)
    deductible_min: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        comment="회당 공제 최저액(원)"
    )

    # 1회 한도(원)
    per_visit_limit: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        comment="1회 한도(원)"
    )

    # 항목별 연간 한도(원)
    annual_limit: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        comment="항목별 연간 한도(원)"
    )

    # 합산캡 그룹 코드(예: 'SL_INOUT_5000')
    combined_cap_group: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="합산캡 그룹 코드(예: 'SL_INOUT_5000')"
    )

    # 그룹 연간 합산 한도(원)
    combined_cap_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2),
        comment="그룹 연간 합산 한도(원)"
    )

    # 횟수 제한 (연간/계약당)
    frequency_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="횟수 제한 (연간/계약당)"
    )

    # 횟수 기준 기간: 'year','contract'
    frequency_period: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="횟수 기준 기간: 'year','contract'"
    )

    # UI/설명 표시 순서
    coverage_order: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        comment="UI/설명 표시 순서"
    )

    # 약관 근거(페이지/조항)
    source_ref: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="약관 근거(페이지/조항)"
    )

    # === 관계 설정 ===
    policy: Mapped["InsurancePolicy"] = relationship(back_populates="coverages")
    coverage_item: Mapped["CoverageItem"] = relationship(back_populates="policies")
