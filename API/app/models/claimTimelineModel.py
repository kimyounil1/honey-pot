# app/models/claimTimelineModel.py
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean,
    Numeric, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base  # Base만 패키지에서 가져오기

class ClaimTimeline(Base):
    __tablename__ = "claim_timeline"
    __table_args__ = (UniqueConstraint("chat_id", name="uq_claim_timeline_chat"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(Integer, nullable=False, index=True)

    # InsurancePolicy.id(FK)는 선택
    policy_pk = Column(Integer, ForeignKey("insurance_policy.id"), nullable=True, index=True)
    policy_id = Column(String, nullable=True)   # 외부 policy_id 문자열
    insurer = Column(String, nullable=True)
    product_code = Column(String, nullable=True)

    disease_name = Column(String, nullable=True)
    disease_code = Column(String, nullable=True)  # ICD-10 등

    base_date = Column(Date, nullable=False)      # 기산일(사고/검사일)
    deadline_date = Column(Date, nullable=False)  # 보통 base_date + 3년

    expected_amount = Column(Numeric(18, 2), nullable=True)
    currency = Column(String, default="KRW")

    source_message_id = Column(Integer, nullable=True)  # 근거 메시지 id
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
