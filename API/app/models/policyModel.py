# app/models/policyModel.py
from . import Column, Integer, String, Date, Text, ForeignKey, relationship, Base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import UniqueConstraint

class InsurancePolicy(Base):
    __tablename__ = "insurance_policy"

    # ✅ PK를 id로
    id = Column(Integer, primary_key=True, index=True)

    # 소유자
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)

    # ✅ OpenSearch 메타와 1:1: policy_id(문자), insurer, product_code, version, effective_date
    policy_id = Column(String(128), unique=True, index=True, nullable=True)  # OS에 들어가는 policy_id(문자열)
    insurer = Column(String(255))             # (기존 insurance_company → rename)
    product_code = Column(String(100))
    version = Column(String(100))
    effective_date = Column(Date)

    # 기존 필드들 유지
    policy_type = Column(String(100))
    coverage_summary = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)

    # ✅ 폴리시에 매핑된 보장 항목명 리스트(검색/OS 메타 동기화용)
    coverage_item_names = Column(JSONB, nullable=False, default=list)

    # 관계
    user = relationship("User", back_populates="insurance_policies")
    claims = relationship("Claim", back_populates="policy")
    predictions = relationship("Prediction", back_populates="policy")

    # 보장 매핑
    # app/models/policyModel.py (발췌)
    coverages = relationship("PolicyCoverage", back_populates="policy", cascade="all, delete-orphan")
    coverage_items = relationship("CoverageItem", secondary="policy_coverage", viewonly=True)

    __table_args__ = (
        UniqueConstraint("policy_id", name="uq_insurance_policy_policy_id"),
    )
