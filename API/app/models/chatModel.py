from . import Column, Integer, String, DateTime, ForeignKey, Base, relationship, Enum, Text, MutableList, PickleType
import datetime


# 채팅방(대화) 테이블
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)  # 특정 채팅 세션을 구분하는 기본키
    user_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(MutableList.as_mutable(PickleType), default=[])
    created_at = Column(DateTime, default=datetime.datetime.now())
    updated_at = Column(DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now())

    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Chat(id='{self.id}', title='{self.title}')>"
    
# 개별 메세지 테이블
class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 'chats.id'를 외래 키로 설정하여 'Chat' 모델과 연결합니다.
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False, index=True)
    role = Column(Enum('user', 'assistant', name='role_enum'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now())
    type = Column(String(50), default="general")
    state = Column(Enum('commencing', 'classifying', 'analyzing', 'searching', 'building', 'done', 'failed', 'complete', name="state_enum"), nullable=False)

    # Chat 모델과의 관계를 정의합니다.
    chat = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return f"<Message(id='{self.id}', role='{self.role}')>"