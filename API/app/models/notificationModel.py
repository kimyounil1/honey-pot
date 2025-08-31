# app/models/notificationModel.py
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, Boolean, Text, Index
)
from sqlalchemy.sql import func
from app.models import Base  # Base만 패키지에서 가져오기

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    timeline_id = Column(Integer, ForeignKey("claim_timeline.id"), nullable=False, index=True)

    # 노출 대상 일자(로그인 시 이 날짜 <= 오늘 인 알림을 내려줌)
    send_on = Column(Date, nullable=False)
    deadline_date = Column(Date, nullable=False)   # 최종 마감일(참고)

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    # 상태
    is_sent = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    priority = Column(Integer, default=5)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 인덱스
Index("idx_notifications_user_send", Notification.user_id, Notification.send_on)
