# from sqlalchemy import Column, Integer, String, ForeignKey
# # from database import Base

# class ChatHistory(Base):
#     __tablename__ = "chat_history"
#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
#     user_chat_idx = Column(Integer, nullable=False)
#     idx = Column(Integer, nullable=False)
#     body = Column(String, nullable=False)
