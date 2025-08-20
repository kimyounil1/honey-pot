from typing import List
from . import BaseModel, datetime, Optional

class NewChat(BaseModel):
    user_id: int
    title: str

class Chat(BaseModel):
    id: int
    title: str
    type: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Message(BaseModel):
    chat_id: int
    role: str
    content: str
    type: str
    state: str

    class Config:
        orm_mode = True
    # created_at: datetime

class MessageStateResponse(BaseModel):
    state: str