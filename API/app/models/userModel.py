from . import Column, Integer, String, Date, DateTime, Float, Text, ForeignKey, relationship, Base

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

class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"))
    timestamp = Column(DateTime)
    user_question = Column(Text)
    ai_response = Column(Text)

    user = relationship("User", back_populates="chat_histories")

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