from . import BaseModel, datetime, Optional

class NewChat(BaseModel):
    user_id: int
    title: str
    type: str = "general"
    # created_at: date
    # updated_at: date

class Chat(BaseModel):
    id: int
    title: str
    type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Message(BaseModel):
    chat_id: int
    role: str
    content: str
    
    class Config:
        orm_mode = True
    # created_at: datetime