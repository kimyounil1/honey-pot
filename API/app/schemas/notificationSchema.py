# app/schemas/notificationSchema.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class NotificationBase(BaseModel):
    user_id: int
    timeline_id: int
    send_on: date
    deadline_date: date
    title: str
    message: str
    is_sent: bool = False
    is_read: bool = False
    priority: int = 5

class NotificationCreate(NotificationBase):
    pass

class NotificationRead(NotificationBase):
    id: int
    class Config:
        orm_mode = True
