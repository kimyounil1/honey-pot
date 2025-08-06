from . import BaseModel, date, Optional

class ClaimBase(BaseModel):
    claim_date: Optional[date]
    claimed_amount: Optional[float]
    approved_amount: Optional[float]
    status: Optional[str]

class ClaimCreate(ClaimBase):
    user_id: int
    policy_id: int

class ClaimRead(ClaimBase):
    claim_id: int
    user_id: int
    policy_id: int
    class Config:
        orm_mode = True
