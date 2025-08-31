# app/schemas/claimTimelineSchema.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class ClaimTimelineBase(BaseModel):
    user_id: int
    chat_id: int
    policy_pk: Optional[int] = None
    policy_id: Optional[str] = None
    insurer: Optional[str] = None
    product_code: Optional[str] = None
    disease_name: Optional[str] = None
    disease_code: Optional[str] = None
    base_date: date
    deadline_date: date
    expected_amount: Optional[float] = None
    currency: Optional[str] = "KRW"
    source_message_id: Optional[int] = None
    notes: Optional[str] = None

class ClaimTimelineCreate(ClaimTimelineBase):
    pass

class ClaimTimelineRead(ClaimTimelineBase):
    id: int
    class Config:
        orm_mode = True
