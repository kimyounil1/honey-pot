from . import BaseModel, date, Optional

class ChatBase(BaseModel):
    user_id: int
    user_chat_idx: int

class ChatHistory(ChatBase):
    idx: int
    body: str