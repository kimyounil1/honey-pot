from . import Column, Integer, String, Date, DateTime, Float, Text, ForeignKey, relationship, Base

class Claim(Base):
    __tablename__ = "claim"

    claim_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"))
    policy_id = Column(Integer, ForeignKey("insurance_policy.policy_id"))
    claim_date = Column(Date)
    claimed_amount = Column(Float)
    approved_amount = Column(Float)
    status = Column(String(50))

    user = relationship("User", back_populates="claims")
    policy = relationship("InsurancePolicy", back_populates="claims")