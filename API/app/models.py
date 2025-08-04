# app/models.py
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    birth_date = Column(Date)

    insurance_policies = relationship("InsurancePolicy", back_populates="user")
    chat_histories = relationship("ChatHistory", back_populates="user")
    documents = relationship("Document", back_populates="user")
    claims = relationship("Claim", back_populates="user")
    predictions = relationship("Prediction", back_populates="user")
    ai_analyses = relationship("AIAnalysis", back_populates="user")


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


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"))
    timestamp = Column(DateTime)
    user_question = Column(Text)
    ai_response = Column(Text)

    user = relationship("User", back_populates="chat_histories")


class CaseExample(Base):
    __tablename__ = "case_example"

    case_id = Column(Integer, primary_key=True, index=True)
    age_group = Column(String(50))
    insurance_type = Column(String(100))
    payout_amount = Column(Float)
    case_description = Column(Text)


class Document(Base):
    __tablename__ = "document"

    document_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    file_name = Column(String(255))
    file_type = Column(String(50))
    upload_date = Column(Date)
    ocr_result = Column(Text)

    user = relationship("User", back_populates="documents")
    ai_analyses = relationship("AIAnalysis", back_populates="document")


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


class Prediction(Base):
    __tablename__ = "prediction"

    prediction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    policy_id = Column(Integer, ForeignKey("insurance_policy.policy_id"))
    expected_amount = Column(Float)
    prediction_date = Column(Date)
    rationale = Column(Text)

    user = relationship("User", back_populates="predictions")
    policy = relationship("InsurancePolicy", back_populates="predictions")


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    analysis_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"))
    document_id = Column(Integer, ForeignKey("document.document_id"))
    summary = Column(Text)
    recommendation = Column(Text)
    analysis_date = Column(Date)

    user = relationship("User", back_populates="ai_analyses")
    document = relationship("Document", back_populates="ai_analyses")
