from . import Column, Integer, String, Date, DateTime, Float, Text, ForeignKey, relationship, Base

class InsurancePolicy(Base):
    __tablename__ = "insurance_policy"

    policy_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    insurance_company = Column(String(255))
    policy_type = Column(String(100))
    coverage_summary = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)

    user = relationship("User", back_populates="insurance_policies")
    claims = relationship("Claim", back_populates="policy")
    predictions = relationship("Prediction", back_populates="policy")

class CaseExample(Base):
    __tablename__ = "case_example"

    case_id = Column(Integer, primary_key=True, index=True)
    age_group = Column(String(50))
    insurance_type = Column(String(100))
    payout_amount = Column(Float)
    case_description = Column(Text)